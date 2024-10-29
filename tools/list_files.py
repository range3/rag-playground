import click
from pathlib import Path


def recursive_list_files(directory: Path):
    for file in directory.iterdir():
        if file.is_dir():
            yield from recursive_list_files(file)
        else:
            yield file


@click.group()
def cli():
    pass

@cli.command()
@click.argument('dirs', type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True), nargs=-1, required=True)
def list_files(dirs):
    """List all files in directories."""
    for directory in dirs:
        directory = Path(directory)
        for file in recursive_list_files(directory):
            relative_path = file.relative_to(directory) 
            click.echo(relative_path.as_posix().replace('/', '_'))

@cli.command()
@click.argument('src_dir', nargs=1, type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True), required=True)
@click.argument('link_dir', nargs=1, type=click.Path(file_okay=False, dir_okay=True, resolve_path=True), required=True)
def create_symlinks(src_dir, link_dir):
    """
    Recursively explore files in source_dir and create symbolic links in target_dir
    with unique file names based on relative paths.
    """
    src_path = Path(src_dir)
    link_path = Path(link_dir)

    # Ensure the target directory exists
    link_path.mkdir(parents=True, exist_ok=True)

    for file in recursive_list_files(src_path):
        # Calculate the relative path from source directory and create a unique name
        relative_path = file.relative_to(src_path)
        unique_name = relative_path.as_posix().replace('/', '_')

        # Create the symlink path in the target directory
        symlink_path = link_path / unique_name

        try:
            # Create a symbolic link
            symlink_path.symlink_to(file)
        except FileExistsError:
            click.echo(f"Skipped (already exists): {symlink_path}", err=True)
        except Exception as e:
            click.echo(f"Error creating symlink {symlink_path}: {e}", err=True)


def main():
    cli()


if __name__ == '__main__':
    main()
