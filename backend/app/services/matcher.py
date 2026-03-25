import numpy as np  # type: ignore
import pickle
import os
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
from app.config import settings  # type: ignore

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

    def match(self, query_embedding: np.ndarray, custom_threshold: float | None = None):
        """
        Match a query embedding against all stored embeddings.
        Automatically uses KNN or max-similarity based on settings.
        """
        if settings.USE_KNN_MATCHING:
            return self.match_knn(query_embedding, k=settings.KNN_NEIGHBORS, custom_threshold=custom_threshold)
            
        if not self.embeddings:
            return None, 0.0

        query = np.array(query_embedding).reshape(1, -1)
        threshold = custom_threshold if custom_threshold is not None else self.threshold

        best_match_id = None
        max_sim = 0.0

        # Compare against all embeddings for all persons
        for person_id, person_data in self.embeddings.items():
            # Validate model consistency
            db_model = person_data.get('model_name')
            if db_model and db_model != self.model_name:
                print(f"WARNING: Model mismatch for person {person_id}. DB: {db_model}, Query: {self.model_name}")

            emb_list = person_data.get('embeddings', [])
            # Get max similarity across all embeddings for this person
            person_max_sim = 0.0
            for emb in emb_list:
                sim = cosine_similarity(query, emb)[0][0]
                if sim > person_max_sim:  # type: ignore
                    person_max_sim = sim

            if person_max_sim > max_sim:  # type: ignore
                max_sim = person_max_sim
                best_match_id = person_id

        if float(max_sim) > float(threshold):  # type: ignore
            return best_match_id, max_sim

        return None, max_sim

    def match_knn(self, query_embedding: np.ndarray, k: int = 5, custom_threshold: float | None = None):
        """
        K-nearest neighbors matching with weighted voting.
        More robust for persons with multiple embeddings.
        Uses weighted voting where higher similarities count more.

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
            similarities.append((person_id, float(sim)))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Take top k
        top_k = similarities[:k]

        # Weighted voting - higher similarities get more weight
        person_weights: dict = {}
        person_weighted_sum: dict = {}

        for i, (person_id, sim) in enumerate(top_k):
            # Weight by similarity and position (top matches count more)
            position_weight = 1.0 / (i + 1)  # Higher rank = higher weight
            weight = sim * position_weight

            if person_id not in person_weights:
                person_weights[person_id] = 0.0
                person_weighted_sum[person_id] = 0.0

            person_weights[person_id] += weight
            person_weighted_sum[person_id] += sim * weight

        # Find winner by weighted score
        best_person_id = None
        best_weighted_score = 0.0
        best_avg_sim = 0.0

        for person_id, total_weight in person_weights.items():
            if total_weight > best_weighted_score:
                best_person_id = person_id
                best_weighted_score = total_weight
                best_avg_sim = person_weighted_sum[person_id] / max(total_weight, 0.001)

        # Check against threshold
        if best_person_id is not None and float(best_avg_sim) > float(threshold):
            return best_person_id, best_avg_sim

        return None, best_avg_sim
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
        top_k = similarities[:k]  # type: ignore

        # Vote by person_id
        vote_count: dict = {}
        vote_score: dict = {}
        for person_id, sim in top_k:
            if person_id not in vote_count:
                vote_count[person_id] = 0
                vote_score[person_id] = 0.0
            vote_count[person_id] = float(vote_count.get(person_id, 0)) + 1  # type: ignore
            vote_score[person_id] = float(vote_score.get(person_id, 0.0)) + float(sim)  # type: ignore

        # Find winner by vote count, then by average similarity
        best_person_id = None
        best_vote_count = 0
        best_avg_sim = 0.0

        for person_id, count in vote_count.items():
            avg_sim = vote_score[person_id] / count
            if count > best_vote_count or (count == best_vote_count and avg_sim > best_avg_sim):  # type: ignore
                best_person_id = person_id
                best_vote_count = count
                best_avg_sim = avg_sim

        # Use average similarity of winning person's top matches
        if best_person_id is not None and float(best_avg_sim) > float(threshold):  # type: ignore
            return best_person_id, best_avg_sim

        return None, best_avg_sim

    def remove_person(self, person_id: int):
        """Remove all embeddings for a person from the fast search DB."""
        if person_id in self.embeddings:
            self.embeddings.pop(person_id, None)
            self.save_db()

matcher = Matcher()
