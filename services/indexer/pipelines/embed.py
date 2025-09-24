"""
Embedding generation pipeline using SentenceTransformers
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import torch
import yaml
from concurrent.futures import ThreadPoolExecutor
import json
import os

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generate embeddings for text chunks using SentenceTransformers"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.model = None
        self.device = self._get_device()
        self._load_model()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            "model_name": "intfloat/e5-base",
            "batch_size": 32,
            "max_seq_length": 512,
            "normalize_embeddings": True,
            "device": "auto",  # auto, cpu, cuda
            "num_workers": 4,
            "cache_dir": "./cache",
            "output_format": "numpy"  # numpy, list
        }
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def _get_device(self) -> str:
        """Determine the best device for embedding generation"""
        device_config = self.config["device"]
        
        if device_config == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            else:
                return "cpu"
        else:
            return device_config
    
    def _load_model(self):
        """Load the SentenceTransformer model"""
        try:
            logger.info(f"Loading embedding model: {self.config['model_name']}")
            
            self.model = SentenceTransformer(
                self.config["model_name"],
                cache_folder=self.config["cache_dir"],
                device=self.device
            )
            
            # Set max sequence length
            self.model.max_seq_length = self.config["max_seq_length"]
            
            logger.info(f"Model loaded successfully on device: {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        if not texts:
            return np.array([])
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            # Generate embeddings in batches
            embeddings = []
            batch_size = self.config["batch_size"]
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Generate embeddings for batch
                batch_embeddings = self.model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=self.config["normalize_embeddings"],
                    show_progress_bar=False
                )
                
                embeddings.append(batch_embeddings)
                
                logger.debug(f"Processed batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            # Concatenate all embeddings
            all_embeddings = np.vstack(embeddings)
            
            logger.info(f"Generated {all_embeddings.shape[0]} embeddings with dimension {all_embeddings.shape[1]}")
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def generate_single_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.generate_embeddings([text])[0]
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process documents and add embeddings to chunks"""
        logger.info(f"Processing {len(documents)} documents for embedding generation")
        
        # Extract all texts that need embeddings
        texts_to_embed = []
        text_to_doc_map = []
        
        for doc_idx, doc in enumerate(documents):
            if "chunks" in doc:
                for chunk_idx, chunk in enumerate(doc["chunks"]):
                    text = chunk.get("text", "")
                    if text.strip():
                        texts_to_embed.append(text)
                        text_to_doc_map.append((doc_idx, chunk_idx))
            else:
                # Document without chunks - embed the full text
                text = doc.get("text", "")
                if text.strip():
                    texts_to_embed.append(text)
                    text_to_doc_map.append((doc_idx, None))
        
        if not texts_to_embed:
            logger.warning("No texts found for embedding generation")
            return documents
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts_to_embed)
        
        # Add embeddings back to documents
        for embedding, (doc_idx, chunk_idx) in zip(embeddings, text_to_doc_map):
            if chunk_idx is not None:
                # Add to chunk
                documents[doc_idx]["chunks"][chunk_idx]["embedding"] = embedding.tolist()
            else:
                # Add to document
                documents[doc_idx]["embedding"] = embedding.tolist()
        
        logger.info(f"Added embeddings to {len(texts_to_embed)} texts")
        return documents
    
    def save_embeddings(self, embeddings: np.ndarray, output_path: str):
        """Save embeddings to file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if output_path.endswith('.npy'):
                np.save(output_path, embeddings)
            elif output_path.endswith('.json'):
                embeddings_list = embeddings.tolist()
                with open(output_path, 'w') as f:
                    json.dump(embeddings_list, f)
            elif output_path.endswith('.txt'):
                np.savetxt(output_path, embeddings)
            else:
                raise ValueError(f"Unsupported output format: {output_path}")
            
            logger.info(f"Saved embeddings to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
            raise
    
    def load_embeddings(self, input_path: str) -> np.ndarray:
        """Load embeddings from file"""
        try:
            if input_path.endswith('.npy'):
                embeddings = np.load(input_path)
            elif input_path.endswith('.json'):
                with open(input_path, 'r') as f:
                    embeddings_list = json.load(f)
                embeddings = np.array(embeddings_list)
            elif input_path.endswith('.txt'):
                embeddings = np.loadtxt(input_path)
            else:
                raise ValueError(f"Unsupported input format: {input_path}")
            
            logger.info(f"Loaded embeddings from {input_path}: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            raise
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        # Ensure embeddings are normalized
        if not self.config["normalize_embeddings"]:
            embedding1 = embedding1 / np.linalg.norm(embedding1)
            embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        return float(np.dot(embedding1, embedding2))
    
    def find_similar_texts(
        self, 
        query_embedding: np.ndarray, 
        text_embeddings: np.ndarray, 
        top_k: int = 10
    ) -> List[tuple]:
        """Find most similar texts to query embedding"""
        # Compute similarities
        similarities = np.dot(text_embeddings, query_embedding)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        return [(idx, similarities[idx]) for idx in top_indices]

def generate_embeddings_for_texts(texts: List[str], model_name: str = "intfloat/e5-base") -> np.ndarray:
    """Convenience function to generate embeddings for texts"""
    generator = EmbeddingGenerator()
    generator.config["model_name"] = model_name
    generator._load_model()
    return generator.generate_embeddings(texts)

def process_documents_with_embeddings(
    documents: List[Dict[str, Any]], 
    config_path: str = None
) -> List[Dict[str, Any]]:
    """Convenience function to process documents and add embeddings"""
    generator = EmbeddingGenerator(config_path)
    return generator.process_documents(documents)

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python embed.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_embedded.json')
    
    # Load documents
    with open(input_file, 'r') as f:
        if input_file.endswith('.jsonl'):
            documents = [json.loads(line) for line in f]
        else:
            documents = json.load(f)
    
    # Process with embeddings
    processed_docs = process_documents_with_embeddings(documents)
    
    # Save results
    with open(output_file, 'w') as f:
        if output_file.endswith('.jsonl'):
            for doc in processed_docs:
                f.write(json.dumps(doc) + '\n')
        else:
            json.dump(processed_docs, f, indent=2)
    
    print(f"Processed {len(processed_docs)} documents with embeddings")
    print(f"Saved to {output_file}")
