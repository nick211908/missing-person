import pickle
import os
import numpy as np

db_path = "c:/Users/Acer/Desktop/face-detection/missing-person-ai/backend/embeddings/db_embeddings.pkl"

if os.path.exists(db_path):
    with open(db_path, "rb") as f:
        data = pickle.load(f)
        print(f"Total persons in DB: {len(data)}")
        for person_id, value in data.items():
            if isinstance(value, dict):
                print(f"Person {person_id}: Model = {value.get('model_name')}, Embeddings = {len(value.get('embeddings', []))}")
                if value.get('embeddings'):
                    print(f"Embedding shape: {np.array(value['embeddings'][0]).shape}")
            else:
                print(f"Person {person_id}: Old format (no metadata)")
            break # Just check the first one
else:
    print("DB not found")
