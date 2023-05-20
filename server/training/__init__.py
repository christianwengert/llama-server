from datasets import load_dataset


data = load_dataset('wikipedia', '20220301.simple', split='train[:10000]')