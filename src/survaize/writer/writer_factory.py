from survaize.writer.cspro_writer import CSProWriter
from survaize.writer.json_writer import JSONWriter
from survaize.writer.writer import Writer


class WriterFactory:
    """Factory for creating writer instances."""

    def __init__(self) -> None:
        self._writers: dict[str, Writer] = {
            "cspro": CSProWriter(),
            "json": JSONWriter(),
        }

    def get(self, output_format: str) -> Writer:
        """Get a writer instance based on the writer type.

        Args:
            output_format: The type of writer to create.

        Returns:
            A writer instance.

        Raises:
            ValueError: If an unsupported writer type is provided.
        """
        writer = self._writers.get(output_format)
        if not writer:
            supported_formats_str = ", ".join(self.get_supported_formats())
            raise ValueError(
                f"Unsupported writer type: {output_format}. Supported formats are: {supported_formats_str}"
            )
        return writer

    def get_supported_formats(self) -> list[str]:
        """Get a list of supported input formats.

        Returns:
            A list of strings representing the supported input formats.
        """
        return list(self._writers.keys())
