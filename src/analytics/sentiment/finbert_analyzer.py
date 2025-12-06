
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import BertTokenizer, BertForSequenceClassification
import numpy as np
import logging
from typing import List, Dict

class FinancialTextDataset(Dataset):
    """
    Dataset class for efficient FinBERT batch tokenization.
    """
    def __init__(self, texts: List[str], tokenizer, max_len: int = 512):
        self.texts = [str(t) for t in texts]
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            return_token_type_ids=False,
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten()
        }

class FinBERTAnalyzer:
    """
    Analyzer using yiyanghkust/finbert-tone for financial sentiment classification.
    """
    def __init__(self, model_name: str = "yiyanghkust/finbert-tone", batch_size: int = 16, device=None):
        self.logger = logging.getLogger(__name__)
        self.batch_size = batch_size
        self.model_name = model_name
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.logger.info(f"Initializing FinBERTAnalyzer with {model_name} on {self.device}")
        
        try:
            self.tokenizer = BertTokenizer.from_pretrained(model_name)
            
            # [FIX] Force low_cpu_mem_usage=False to prevent "meta tensor" error if accelerate is present
            # This ensures the model is fully loaded into CPU RAM before moving.
            self.model = BertForSequenceClassification.from_pretrained(
                model_name, 
                num_labels=3, 
                ignore_mismatched_sizes=True,
                low_cpu_mem_usage=False
            )
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            self.logger.error(f"Failed to load FinBERT model: {e}")
            raise

    def predict(self, texts: List[str]) -> List[Dict[str, float]]:
        """
        Predict sentiment probabilities for a list of texts.
        
        Returns:
            List of dicts, e.g., [{'Neutral': 0.1, 'Positive': 0.8, 'Negative': 0.1}, ...]
        """
        if not texts:
            return []

        dataset = FinancialTextDataset(texts, self.tokenizer)
        data_loader = DataLoader(dataset, batch_size=self.batch_size, num_workers=0) # Windows likes num_workers=0

        probs_list = []
        # yiyanghkust/finbert-tone specific mapping: 0=Neutral, 1=Positive, 2=Negative
        # WARNING: Check config.json if model changes.
        
        try:
            with torch.no_grad():
                gpu_tensors = []
                for batch in data_loader:
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)

                    outputs = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask
                    )
                    
                    logits = outputs.logits
                    probs = torch.nn.functional.softmax(logits, dim=1)
                    # [OPTIMIZATION] Keep on GPU, append to list
                    gpu_tensors.append(probs)
                    
                if not gpu_tensors:
                    return []
                    
                # [OPTIMIZATION] Cat once, transfer once
                all_probs = torch.cat(gpu_tensors, dim=0).cpu().numpy()
                probs_list = all_probs.tolist() # Convert to list of lists [ [n,p,ng], ...]

        except Exception as e:
            self.logger.error(f"Inference failed: {e}")
            return []

        results = []
        for p in probs_list:
            # Map based on yiyanghkust/finbert-tone
            # Label 0: Neutral
            # Label 1: Positive
            # Label 2: Negative
            results.append({
                "Neutral": float(p[0]),
                "Positive": float(p[1]),
                "Negative": float(p[2])
            })
            
        return results
