import click
import os
import shutil
import toml
from pathlib import Path
import questionary
from agenta.docker.docker_utils import build_and_upload_docker_image
from agenta.client import client
from docker.models.images import Image as DockerImage


@click.group()
def cli():
    pass


@click.command(name='add-variant')
@click.argument('project_folder', default='.')
@click.option('--variant_name', default='')
def add_variant(variant_name: str, project_folder: str):
    """Add a new variant."""
    project_path = Path(project_folder)
    config_file = project_path / 'config.toml'
    if not config_file.exists():
        click.echo("Please run agenta init first")
        return
    else:
        config = toml.load(config_file)
        app_name = config['app-name']
        if 'variants' not in config:
            config['variants'] = []

    if not variant_name:
        variant_name = questionary.text('Please enter the variant name').ask()

    if variant_name in config['variants']:
        overwrite = questionary.confirm(
            'This variant already exists. Do you want to overwrite it?').ask()
        if not overwrite:
            click.echo("Operation cancelled.")
            sys.exit(0)
    else:
        config['variants'].append(variant_name)
        toml.dump(config, config_file.open('w'))

    docker_image: DockerImage = build_and_upload_docker_image(
        folder=project_path, variant_name=variant_name)
    client.add_variant_to_server(app_name, variant_name, docker_image)
    click.echo(f"Variant {variant_name} for App {app_name} added")


@click.command()
@click.option('--app_name', default='')
def init(app_name: str):
    """Initialize a new Agenta project with the template files."""
    if not app_name:
        app_name = questionary.text('Please enter the app name').ask()

    config = {"app-name": app_name}
    with open('config.toml', 'w') as config_file:
        toml.dump(config, config_file)

    # Ask for init option
    init_option = questionary.select(
        "How do you want to initialize your project?",
        choices=['Blank Project', 'From Template']
    ).ask()

    # If the user selected the second option, show a list of available templates
    if init_option == 'From Template':
        current_dir = Path.cwd()
        template_dir = Path(__file__).parent / "templates"
        templates = [folder.name for folder in template_dir.iterdir()
                     if folder.is_dir()]
        template_desc = [toml.load(
            (template_dir / name / 'template.toml'))['short_desc'] for name in templates]

        # Show the templates to the user
        template = questionary.select(
            "Which template do you want to use?",
            choices=[questionary.Choice(title=f"{template} - {template_desc}", value=template)
                     for template, template_desc in zip(templates, template_desc)]
        ).ask()

        # Copy the template files to the current directory
        chosen_template_dir = template_dir / template
        for file in chosen_template_dir.glob("*"):
            if file.name != 'template.toml':
                shutil.copy(file, current_dir / file.name)
    click.echo("Project initialized successfully")


@click.command(name='start')
@click.option('--variant_name', default=None)
def start_variant_cli(variant_name: str):
    """Start a variant."""
    project_path = Path('.')
    config_file = project_path / 'config.toml'
    if not config_file.exists():
        click.echo("Please run agenta init first")
        return
    else:
        config = toml.load(config_file)
        app_name = config['app-name']
        if 'variants' not in config:
            click.echo("No variants found. Please add a variant first.")
            return

    if not variant_name:
        variant_name = questionary.select(
            'Please choose a variant',
            choices=config['variants']
        ).ask()

    endpoint = client.start_variant(app_name, variant_name)
    click.echo(
        f"Started variant {variant_name} for App {app_name}. Endpoint: {endpoint}")


# Add the commands to the CLI group
cli.add_command(add_variant)
cli.add_command(init)
cli.add_command(start_variant_cli)

if __name__ == '__main__':
    cli()