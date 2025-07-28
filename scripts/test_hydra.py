from omegaconf import DictConfig, OmegaConf
import hydra
import yaml

import os


DIR_PATH = os.path.dirname(__file__)


@hydra.main(version_base=None, config_path="conf", config_name="config")
def my_app(cfg: DictConfig) -> None:
    print(OmegaConf.to_yaml(cfg))


if __name__ == '__main__':
    my_app()

    # file_path = os.path.join(DIR_PATH, 'test.yaml')
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     data = yaml.safe_load(f)
    #     print("YAML content loaded:")
    #     print(data)
