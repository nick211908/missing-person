import numpy as np
import pickle
import os
from sklearn.metrics.pairwise import cosine_similarity
from app.config import settings

class Matcher:
    def __init__(self):
        self.db_path = settings.EMBEDDING_DB_PATH
        # Dictionary mapping person_id -> list of embeddings (numpy arrays)
        self.embeddings = {}
        self.threshold = settings.SIMILARITY_THRESHOLD
        self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
            with open(self.db_path, "rb") as f:
                data = pickle.load(f)
                # Handle migration from old format (single embedding per person)
                self.embeddings = {}
                for person_id, emb in data.items():
                    if isinstance(emb, list):
                        self.embeddings[person_id] = [np.array(e).reshape(1, -1) for e in emb]
                    else:
                        # Old format - single embedding, convert to list
                        self.embeddings[person_id] = [np.array(emb).reshape(1, -1)]
        else:
            self.embeddings = {}

    def save_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Convert numpy arrays to lists for serialization
        data = {}
        for person_id, emb_list in self.embeddings.items():
            data[person_id] = [emb.tolist() for emb in emb_list]
        with open(self.db_path, "wb") as f:
            pickle.dump(data, f)

    def add_person_embedding(self, person_id: int, embedding: np.ndarray):
        """
        Add a new embedding for a person. Supports multiple embeddings per person.
        """
        if person_id not in self.embeddings:
            self.embeddings[person_id] = []
        self.embeddings[person_id].append(np.array(embedding).reshape(1, -1))
        self.save_db()

    def get_person_embeddings(self, person_id: int) -> list:
        """
        Get all embeddings for a person.
        """
        return self.embeddings.get(person_id, [])

    def compute_self_similarity(self, person_id: int) -> float:
        """
        Compute mean intra-person similarity across all embeddings for a person.
        Used for per-person threshold calibration.
        """
        embeddings = self.embeddings.get(person_id, [])
        if len(embeddings) < 2:
            return 0.0

        # Compute pairwise similarities
        sims = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])[0][0]
                sims.append(sim)

        return float(np.mean(sims)) if sims else 0.0

    def match(self, query_embedding: np.ndarray, custom_threshold: float = None):
        """
        Match a query embedding against all stored embeddings.
        Returns (best_person_id, max_similarity_score) or (None, 0.0)
        For persons with multiple embeddings, uses the maximum similarity across all embeddings.
        """
        if not self.embeddings:
            return None, 0.0

        query = np.array(query_embedding).reshape(1, -1)
        threshold = custom_threshold if custom_threshold is not None else self.threshold

        best_match_id = None
        max_sim = 0.0

        # Compare against all embeddings for all persons
        for person_id, emb_list in self.embeddings.items():
            # Get max similarity across all embeddings for this person
            person_max_sim = 0.0
            for emb in emb_list:
                sim = cosine_similarity(query, emb)[0][0]
                if sim > person_max_sim:
                    person_max_sim = sim

            if person_max_sim > max_sim:
                max_sim = person_max_sim
                best_match_id = person_id

        if max_sim > threshold:
            return best_match_id, max_sim

        return None, max_sim

    def remove_person(self, person_id: int):
        """Remove all embeddings for a person from the fast search DB."""
        if person_id in self.embeddings:
            del self.embeddings[person_id]
            self.save_db()

matcher = Matcher()
