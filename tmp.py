from omegaconf import DictConfig, OmegaConf
from omegaconf.basecontainer import BaseContainer
import hydra
from pprint import pprint


# @hydra.main(version_base=None, config_path=".", config_name="code/verl/trainer/config")
# def my_app(cfg: DictConfig):
#     assert cfg.node.loompa == 10          # attribute style access
#     assert cfg["node"]["loompa"] == 10    # dictionary style access

#     assert cfg.node.zippity == 10         # Value interpolation
#     assert isinstance(cfg.node.zippity, int)  # Value interpolation type
#     assert cfg.node.do == "oompa 10"      # string interpolation

#     # cfg.node.waldo                        # raises an exception
#     print(cfg)
#     print(f"zippity: {cfg.node.zippity}")


@hydra.main(version_base=None, config_path="./code/verl/trainer/config", config_name="ppo_trainer")
def my_app(cfg: DictConfig):
    # pprint(cfg)
    c = BaseContainer._to_content(cfg, True, throw_on_missing=False)
    print(f"type of c: {type(c)}")
    import json
    with open(
        '/root/data1/projects/RL/DeepRetrieval/tmp.json',
        'w',
        encoding='utf-8'
    ) as f:
        json.dump(c, f, ensure_ascii=False)


if __name__ == "__main__":
    my_app()
