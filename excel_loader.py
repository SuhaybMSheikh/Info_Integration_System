import pandas as pd

def load_excel(path: str) -> pd.DataFrame: #will return a dataframe from an excel file
    df = pd.read_excel(path)

    df.columns = [c.strip() for c in df.columns]

    return df