from data_fetcher import fetch_data

df = fetch_data()
print("✅ Shape:", df.shape)
print("✅ Columns:", df.columns.tolist())
print("✅ First row:", df.iloc[0].to_dict())