#!/usr/bin/env python3
import json
from pathlib import Path

from mlx_lm import server as mlx_server


def model_aliases(model_path):
    path = Path(model_path).expanduser()
    if not path.exists():
        return {}
    return {path.name: str(path.resolve())}


_original_model_provider_init = mlx_server.ModelProvider.__init__


def model_provider_init(self, cli_args):
    _original_model_provider_init(self, cli_args)
    aliases = model_aliases(cli_args.model)
    self.model_aliases = aliases
    for alias, target in aliases.items():
        self._model_map[alias] = target


def handle_models_request(self):
    self._set_completion_headers(200)
    self.end_headers()

    files = ["config.json", "model.safetensors.index.json", "tokenizer_config.json"]
    parts = self.path.split("/")
    filter_repo_id = None
    if len(parts) > 3:
        filter_repo_id = "/".join(parts[3:])

    def probably_mlx_lm(repo):
        if repo.repo_type != "model":
            return False
        if "main" not in repo.refs:
            return False
        if filter_repo_id is not None and repo.repo_id != filter_repo_id:
            return False
        file_names = {f.file_path.name for f in repo.refs["main"].files}
        return all(f in file_names for f in files)

    hf_cache_info = mlx_server.scan_cache_dir()
    downloaded_models = [
        repo for repo in hf_cache_info.repos if probably_mlx_lm(repo)
    ]

    models = []
    seen_model_ids = set()

    def add_model(model_id):
        if not model_id or model_id in seen_model_ids:
            return
        seen_model_ids.add(model_id)
        models.append(
            {
                "id": model_id,
                "object": "model",
                "created": self.created,
            }
        )

    for alias in getattr(self.response_generator.model_provider, "model_aliases", {}):
        add_model(alias)

    for repo in downloaded_models:
        add_model(repo.repo_id)

    if self.response_generator.cli_args.model:
        model_path = Path(self.response_generator.cli_args.model)
        if model_path.exists():
            add_model(str(model_path.resolve()))

    response = {"object": "list", "data": models}
    self.wfile.write(json.dumps(response).encode())
    self.wfile.flush()


mlx_server.ModelProvider.__init__ = model_provider_init
mlx_server.APIHandler.handle_models_request = handle_models_request


if __name__ == "__main__":
    mlx_server.main()
