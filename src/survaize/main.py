"""Command-line interface for Survaize."""

import logging
import os
import threading
import webbrowser
from pathlib import Path
from typing import Literal

import click
import logfire
from dotenv import load_dotenv
from rich.console import Console

from survaize.config.llm_config import LLMConfig, OpenAIProviderType
from survaize.convert.converter import QuestionnaireConverter
from survaize.web.backend.server import run_server

# Load environment variables from .env file if present
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# For console UI
console = Console()
OutputFormat = Literal["json", "cspro", "surveysolutions"]


def configure_logfire():
    # Token is read from LOGFIRE_TOKEN environment variable by default
    # and is disabled if not present.
    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_openai()


@click.group()
def cli() -> None:
    """Survaize - generate mobile survey apps from questionnaires ."""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_file", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["cspro", "json", "surveysolutions"]),
    default="json",
    help="Output format for the questionnaire",
)
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    help="OpenAI API key (can also be set via OPENAI_API_KEY env var)",
    required=True,
)
@click.option(
    "--api-provider",
    type=click.Choice(["openai", "azure"]),
    default="openai",
    envvar="OPENAI_PROVIDER",
    help="OpenAI API provider type, can also be set via OPENAI_PROVIDER environment variable",
)
@click.option(
    "--api-version",
    envvar="OPENAI_API_VERSION",
    help="OpenAI API version for Azure only (can also be set via OPENAI_API_VERSION env var)",
)
@click.option(
    "--api-url",
    envvar="OPENAI_API_URL",
    help="OpenAI API URL required for Azure (can also be set via OPENAI_API_URL env var)",
)
@click.option(
    "--api-model",
    envvar="OPENAI_API_MODEL",
    default="gpt-4.1",
    help="OpenAI API model name (can also be set via OPENAI_API_MODEL env var). Defaults to gpt-4.1",
)
def convert(
    input_file: Path,
    output_file: Path,
    output_format: OutputFormat,
    api_key: str,
    api_provider: OpenAIProviderType | None,
    api_version: str | None,
    api_url: str | None,
    api_model: str,
) -> None:
    """Convert a questionnaire to the specified format."""

    configure_logfire()
    logfire.info("Start convert", input_file=input_file, output_file=output_file, output_format=output_format)

    if api_provider == OpenAIProviderType.AZURE:
        if not api_url:
            raise click.UsageError(
                "Azure requires a url for the API endpoint "
                + "Please provide it via the --api-url argument or the OPENAI_API_URL environment variable."
            )
        api_version = api_version or "2025-04-01-preview"

    try:
        llm_config = LLMConfig(
            api_key=api_key,
            api_version=api_version,
            api_url=api_url,
            model=api_model,
            provider=OpenAIProviderType(api_provider),
        )

        converter = QuestionnaireConverter(llm_config=llm_config)

        # Convert using the pipeline architecture
        converter.convert(input_file=input_file, output_file=output_file, output_format=output_format)

        console.log(f"[green]Successfully converted {input_file} to {output_file}")

    except Exception as e:
        console.log(f"[red]Error during conversion: {e}")
        logger.exception("Conversion failed")
        raise


@cli.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind the web server to",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to bind the web server to",
)
@click.option(
    "--reload/--no-reload",
    default=False,
    help="Reload the server when code changes",
)
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    help="OpenAI API key (can also be set via OPENAI_API_KEY env var)",
    required=True,
)
@click.option(
    "--api-provider",
    type=click.Choice(["openai", "azure"]),
    default="openai",
    envvar="OPENAI_PROVIDER",
    help="OpenAI API provider type, can also be set via OPENAI_PROVIDER environment variable",
)
@click.option(
    "--api-version",
    envvar="OPENAI_API_VERSION",
    help="OpenAI API version for Azure only (can also be set via OPENAI_API_VERSION env var)",
)
@click.option(
    "--api-url",
    envvar="OPENAI_API_URL",
    help="OpenAI API URL required for Azure (can also be set via OPENAI_API_URL env var)",
)
@click.option(
    "--api-model",
    envvar="OPENAI_API_MODEL",
    default="gpt-4.1",
    help="OpenAI API model name (can also be set via OPENAI_API_MODEL env var). Defaults to gpt-4.1",
)
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Do not open the web UI in a browser automatically",
)
def ui(
    host: str,
    port: int,
    reload: bool,
    api_key: str,
    api_provider: OpenAIProviderType | None,
    api_version: str | None,
    api_url: str | None,
    api_model: str,
    no_browser: bool,
) -> None:
    """Start the Survaize web application server."""
    configure_logfire()

    try:
        if api_provider == OpenAIProviderType.AZURE:
            if not api_url:
                raise click.UsageError(
                    "Azure requires a url for the API endpoint "
                    + "Please provide it via the --api-url argument or the OPENAI_API_URL environment variable."
                )
            api_version = api_version or "2025-04-01-preview"

        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_PROVIDER"] = str(api_provider)
        if api_version:
            os.environ["OPENAI_API_VERSION"] = api_version
        if api_url:
            os.environ["OPENAI_API_URL"] = api_url
        os.environ["OPENAI_API_MODEL"] = api_model

        if not no_browser:
            url = f"http://{host}:{port}"
            console.log(f"[green]Opening {url} in your browser...[/green]")
            threading.Timer(1.0, webbrowser.open, args=(url,)).start()

        run_server(host=host, port=port, reload=reload)
    except Exception as e:
        console.log(f"[red]Error starting web server: {e}")
        logger.exception("Web server failed to start")
        raise


if __name__ == "__main__":
    cli()
