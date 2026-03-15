import numpy as np
import pickle
import os
from sklearn.metrics.pairwise import cosine_similarity
from app.config import settings

class Matcher:
    def __init__(self):
        self.db_path = settings.EMBEDDING_DB_PATH
        # Dictionary mapping person_id -> {'embeddings': [...], 'model_name': str}
        self.embeddings = {}
        self.model_name = settings.FACE_MODEL
        self.threshold = settings.SIMILARITY_THRESHOLD
        self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
            with open(self.db_path, "rb") as f:
                data = pickle.load(f)
                # Handle migration from old format (single embedding per person)
                self.embeddings = {}
                for person_id, value in data.items():
                    # Check if new format with metadata
                    if isinstance(value, dict):
                        self.embeddings[person_id] = {
                            'embeddings': [np.array(e).reshape(1, -1) for e in value.get('embeddings', [])],
                            'model_name': value.get('model_name', 'ArcFace')
                        }
                    elif isinstance(value, list):
                        # Intermediate format - list of embeddings
                        self.embeddings[person_id] = {
                            'embeddings': [np.array(e).reshape(1, -1) for e in value],
                            'model_name': 'ArcFace'
                        }
                    else:
                        # Old format - single embedding, convert to new format
                        self.embeddings[person_id] = {
                            'embeddings': [np.array(value).reshape(1, -1)],
                            'model_name': 'ArcFace'
                        }
        else:
            self.embeddings = {}

    def save_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Convert numpy arrays to lists for serialization
        data = {}
        for person_id, person_data in self.embeddings.items():
            data[person_id] = {
                'embeddings': [emb.tolist() for emb in person_data['embeddings']],
                'model_name': person_data.get('model_name', self.model_name)
            }
        with open(self.db_path, "wb") as f:
            pickle.dump(data, f)

    def add_person_embedding(self, person_id: int, embedding: np.ndarray):
        """
        Add a new embedding for a person. Supports multiple embeddings per person.
        """
        if person_id not in self.embeddings:
            self.embeddings[person_id] = {
                'embeddings': [],
                'model_name': self.model_name
            }
        self.embeddings[person_id]['embeddings'].append(np.array(embedding).reshape(1, -1))
        self.save_db()

    def get_person_embeddings(self, person_id: int) -> list:
        """
        Get all embeddings for a person.
        """
        person_data = self.embeddings.get(person_id, {})
        return person_data.get('embeddings', [])

    def compute_self_similarity(self, person_id: int) -> float:
        """
        Compute mean intra-person similarity across all embeddings for a person.
        Used for per-person threshold calibration.
        """
        embeddings = self.get_person_embeddings(person_id)
        if len(embeddings) < 2:
            return 0.0

        # Compute pairwise similarities
        sims = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])[0][0]
                sims.append(sim)

        return float(np.mean(sims)) if sims else 0.0

    def compute_self_similarity_std(self, person_id: int) -> float:
        """
        Compute standard deviation of intra-person similarity.
        Low variance indicates nearly identical embeddings.
        """
        embeddings = self.get_person_embeddings(person_id)
        if len(embeddings) < 2:
            return 1.0

        # Compute pairwise similarities
        sims = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])[0][0]
                sims.append(sim)

        return float(np.std(sims)) if sims else 1.0

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
        for person_id, person_data in self.embeddings.items():
            emb_list = person_data.get('embeddings', [])
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

    def match_knn(self, query_embedding: np.ndarray, k: int = 3, custom_threshold: float = None):
        """
        K-nearest neighbors matching with voting.
        More robust for persons with multiple embeddings.

        Args:
            query_embedding: The embedding to match
            k: Number of neighbors to consider
            custom_threshold: Optional threshold override

        Returns:
            Tuple of (best_person_id, confidence_score) or (None, 0.0)
        """
        if not self.embeddings:
            return None, 0.0

        query = np.array(query_embedding).reshape(1, -1)
        threshold = custom_threshold if custom_threshold is not None else self.threshold

        # Collect all embeddings with their person_ids
        all_embeddings = []
        for person_id, person_data in self.embeddings.items():
            for emb in person_data.get('embeddings', []):
                all_embeddings.append((person_id, emb))

        if len(all_embeddings) == 0:
            return None, 0.0

        # Compute similarities to all embeddings
        similarities = []
        for person_id, emb in all_embeddings:
            sim = cosine_similarity(query, emb)[0][0]
            similarities.append((person_id, sim))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Take top k
        top_k = similarities[:k]

        # Vote by person_id
        vote_count = {}
        vote_score = {}
        for person_id, sim in top_k:
            if person_id not in vote_count:
                vote_count[person_id] = 0
                vote_score[person_id] = 0.0
            vote_count[person_id] += 1
            vote_score[person_id] += sim

        # Find winner by vote count, then by average similarity
        best_person_id = None
        best_vote_count = 0
        best_avg_sim = 0.0

        for person_id, count in vote_count.items():
            avg_sim = vote_score[person_id] / count
            if count > best_vote_count or (count == best_vote_count and avg_sim > best_avg_sim):
                best_person_id = person_id
                best_vote_count = count
                best_avg_sim = avg_sim

        # Use average similarity of winning person's top matches
        if best_person_id is not None and best_avg_sim > threshold:
            return best_person_id, best_avg_sim

        return None, best_avg_sim

    def remove_person(self, person_id: int):
        """Remove all embeddings for a person from the fast search DB."""
        if person_id in self.embeddings:
            del self.embeddings[person_id]
            self.save_db()

matcher = Matcher()
