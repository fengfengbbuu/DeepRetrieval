import datasets
from typing import Literal


parquet_file: str = "/path/to/parquet"
split_name: Literal['train', 'val', 'test']

dataframe = datasets.load_dataset("parquet", data_files=parquet_file)[split_name]
print(dataframe)

# Output:
# Dataset({
#     features: ['question', 'db_id', 'sql', 'data_source', 'prompt', 'ability', 'reward_model', 'extra_info'],
#     num_rows: 8357
# })
