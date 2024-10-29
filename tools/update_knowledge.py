import os
import json
import click
from pathlib import Path
from dify_client.client import KnowledgeBaseClient


def fetch_dataset_id(client, dataset_name, page_size=100):
    """Fetch the ID of a dataset by its name, considering pagination."""
    page = 1
    while True:
        response = client.list_datasets(page=page, page_size=page_size)
        if response.status_code == 200:
            datasets = response.json().get('data', [])
            for dataset in datasets:
                if dataset.get("name") == dataset_name:
                    return dataset.get("id")
            if len(datasets) < page_size:
                break
            page += 1
        else:
            raise Exception(f"Failed to retrieve datasets. Status code: {
                            response.status_code}")
    return None


@click.group()
@click.option('--api-key', required=True, help='Dify API key', envvar='DIFY_API_KEY')
@click.option('--base-url', default='http://rag-playground-nginx-1/v1', help='Dify base URL', envvar='DIFY_BASE_URL')
@click.pass_context
def cli(ctx, api_key, base_url):
    """A command-line tool for managing knowledge."""
    ctx.ensure_object(dict)
    ctx.obj['API_KEY'] = api_key
    ctx.obj['BASE_URL'] = base_url


@cli.command()
@click.option('--dataset-name', default='proceedings', help='Name of the dataset to look up')
@click.pass_context
def get_dataset_id(ctx, dataset_name):
    """Look up and print the ID of a dataset by its name."""
    try:
        api_key = ctx.obj['API_KEY']
        base_url = ctx.obj['BASE_URL']

        client = KnowledgeBaseClient(api_key=api_key, base_url=base_url)

        dataset_id = fetch_dataset_id(client, dataset_name)
        if dataset_id:
            click.echo(f"{dataset_id}")
        else:
            click.echo(f"No dataset found with the name: {
                       dataset_name}", err=True)
    except Exception as e:
        click.echo(f"An error occurred: {e}", err=True)


def load_uploaded_files(database_file):
    """Load the set of already uploaded files from a database text file."""
    if not os.path.exists(database_file):
        return set()
    with open(database_file, 'r', encoding='utf-8') as db:
        return set(line.strip() for line in db if line.strip())


def save_uploaded_files(db_file_handle, file_path):
    """Save the uploaded file path to the open database file handle."""
    db_file_handle.write(f"{file_path}\n")


def recursive_list_files(paths: list, extensions: set):
    """Recursively list files in the given paths (both files and directories) with specific extensions."""
    for path in paths:
        p = Path(path)
        if p.is_dir():
            for file in p.rglob('*'):
                if file.is_file() and (file.suffix in extensions):
                    yield file
        elif p.is_file() and (p.suffix in extensions):
            yield p

@cli.command()
@click.argument('src', type=click.Path(exists=True, resolve_path=True), nargs=-1, required=True)
@click.option('--dataset-name', default='proceedings', help='Name of the dataset to add the files to')
@click.option('--extensions', default='txt,md,pdf', help='Comma-separated list of file extensions to include (default: txt, md, pdf)')
@click.option('--database-file', default='uploaded_files.txt', type=click.Path(), help='Path to the text file that stores the list of uploaded files')
@click.pass_context
def add(ctx, src, dataset_name, extensions, database_file):
    """Add files from source paths (files or directories) to a specified dataset, skipping already uploaded files."""
    try:
        api_key = ctx.obj['API_KEY']
        base_url = ctx.obj['BASE_URL']

        client = KnowledgeBaseClient(api_key=api_key, base_url=base_url)

        dataset_id = fetch_dataset_id(client, dataset_name)
        if not dataset_id:
            click.echo(f"No dataset found with the name: {dataset_name}", err=True)
            return
        client.dataset_id = dataset_id

        # Load the set of uploaded files from the database
        uploaded_files = load_uploaded_files(database_file)

        # Convert the extensions to a set of suffixes with leading dots
        extensions_set = {f".{ext.strip()}" for ext in extensions.split(",")}

        # Open the database file for appending successfully uploaded files
        with open(database_file, 'a', encoding='utf-8') as db_file_handle:
            # Recursively find files in the source paths
            for file in recursive_list_files(src, extensions_set):
                full_path = str(file.resolve())

                # Check if the file is already uploaded
                if full_path in uploaded_files:
                    click.echo(f"File already uploaded, skipping: {full_path}")
                    continue

                # Upload the file
                response = client.create_document_by_file(file_path=full_path)
                if response.status_code == 200:
                    # Update the database with the newly uploaded file
                    save_uploaded_files(db_file_handle, full_path)
                    uploaded_files.add(full_path)
                else:
                    click.echo(f"Failed to add file '{full_path}'. Status code: {response.status_code}", err=True)
    except Exception as e:
        click.echo(f"An error occurred: {e}", err=True)


@cli.command()
@click.option('--dataset-name', required=True, help='Name of the dataset to search in')
@click.option('--keyword', default='', help='Keyword to search for in the documents')
@click.pass_context
def search(ctx, dataset_name, keyword):
    """Search for documents in a specified dataset using an optional keyword."""
    try:
        api_key = ctx.obj['API_KEY']
        base_url = ctx.obj['BASE_URL']

        client = KnowledgeBaseClient(api_key=api_key, base_url=base_url)

        dataset_id = fetch_dataset_id(client, dataset_name)
        if not dataset_id:
            click.echo(f"No dataset found with the name: {
                       dataset_name}", err=True)
            return
        client.dataset_id = dataset_id

        page = 1
        while True:
            response = client.list_documents(
                page=page, page_size=100, keyword=keyword)
            if response.status_code == 200:
                documents = response.json().get('data', [])
                if documents:
                    for doc in documents:
                        click.echo(f"id: {doc.get('id')}, name: {
                                   doc.get('name')}")
                        # click.echo(json.dumps(doc, indent=2, ensure_ascii=False))
            else:
                click.echo(f"Failed to retrieve documents. Status code: {
                           response.status_code}", err=True)
                return

            if not response.json().get("has_more", False):
                break

    except Exception as e:
        click.echo(f"An error occurred: {e}", err=True)


if __name__ == '__main__':
    cli(obj={})
