# Survaize

Survaize is a tool that automatically converts "paper" questionnaires into interactive survey apps. It uses a combination of OCR and generative AI vision models to understand the structure of survey questionnaires in order to generate survey apps compatible with data collection platforms like [CSPro](https://www.census.gov/data/software/cspro.html).

## Features

- Read PDF questionnaires 
- Intelligent survey structure recognition using Generative AI
- Conversion to intermediate JSON format
- Export to popular survey platforms (CSPro, others in the future)

## Installation

Eventually this will be published to PyPy but for now follow the instructions in [installation.md](installation.md).

## Setup
Survaize requires an OpenAI API key. You can specify it using the --api-key parameter or by setting in the OPENAI_API_KEY environment variable.

If you do not already have an account on the [OpenAI developer platform](https://platform.openai.com/docs/overview) you will need to sign up to get a key.

Survaize should also work with other LLM providers that have OpenAI compatible APIs by providing the appropriate API URL and model name via the --api-url and --api-model arguments or the OPENAI_API_URL and OPENAI_MODEL environment variables. Note that only LLMs that support vision will work.

To use Azure OpenAI you will need to specify the key, URL, API version and deployment name. For example:

```
OPENAI_API_KEY="XXXXXXXXXXXXXXXXXXXXXXXX"
OPENAI_API_VERSION="2025-04-01-preview"
OPENAI_API_URL="https://myazuredeploy-openai.openai.azure.com/"
OPENAI_API_DEPLOYMENT="my-gpt-4.1-deployment"
```

Alternatively, you can pass those variables as command line arguments to survaize (run `survaize --help` for details).

## Running
To convert a PDF questionnaire to CSPro run:

```shell
survaize convert input_file output_file --format cspro
```

For example:

```shell
survaize convert examples/PopstanHouseholdQuestionnaire.pdf output/PopstanHouseholdSurvey --format cspro
```
will generate a complete CSPro application (dictionary, forms...) in the directory `output/PopstanHouseholdSurvey`.

Survaize uses JSON as an intermediate format so JSON files can be used as input or output files. The above command could be split into two using an intermediate JSON file:

```shell
survaize convert examples/PopstanHouseholdQuestionnaire.pdf output/PopstanHouseholdSurvey.json --format json
survaize convert output/PopstanHouseholdSurvey.json output/PopstanHouseholdSurvey --format cspro
```

You can even hand edit the intermediate JSON file before generating the CSPro application.

## Development

This project uses Python and UV as the package manager. To install see [installation.md](installation.md).

For development workflows, see [development.md](development.md).

For instructions on publishing to PyPI, see [publishing.md](publishing.md).

## License

MIT 

## TODO
- Use min/max length of numeric fields to add a value set with the range
- Correctly handle location question type (produce two fields in CSPro)
- Fills in CAPI question text
- Evals