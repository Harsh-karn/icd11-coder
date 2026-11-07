import re
import math
from collections import Counter
from typing import List, Dict, Any, Tuple

# Comprehensive clinical synonyms, expansions, and colloquialisms
CLINICAL_ABBREVIATIONS = {
    # Colloquial to medical terminology
    "chickenpox": "varicella chickenpox viral blister rash 1e90",
    "chicken pox": "varicella chickenpox viral blister rash 1e90",
    "shingles": "herpes zoster varicella 1e91",
    "jigger": "tungiasis tunga penetrans embedded flea sandflea 1g05",
    "jiggers": "tungiasis tunga penetrans embedded flea sandflea 1g05",
    "embedded flea": "tungiasis tunga penetrans sandflea 1g05",
    "embedded fleas": "tungiasis tunga penetrans sandflea 1g05",
    "sand flea": "tungiasis tunga penetrans 1g05",
    "bilharzia": "schistosomiasis haematobium river snail blood urine 1f86",
    "schistosoma": "schistosomiasis haematobium mansoni",
    "thrush": "candidosis candidiasis candida yeast fungal",
    "curd-like": "candidosis candidiasis vulvovaginal candida",
    "curd like": "candidosis candidiasis vulvovaginal candida",
    "yeast infection": "candidosis candidiasis vulvovaginal",
    "ringworm": "dermatophytosis tinea fungal skin scalp",
    "scabies": "scabies sarcoptes scabiei mite itch",
    "pink eye": "conjunctivitis eye infection",
    "whooping cough": "pertussis bordetella whooping cough",
    
    # Common clinical acronyms
    "urti": "upper respiratory tract infection nasopharyngitis common cold acute rhinitis",
    "rti": "respiratory tract infection",
    "lrti": "lower respiratory tract infection pneumonia bronchitis",
    "uti": "urinary tract infection cystitis dysuria pyelonephritis",
    "tb": "tuberculosis mycobacterium pulmonary respiratory",
    "ptb": "pulmonary tuberculosis respiratory",
    "copd": "chronic obstructive pulmonary disease emphysema bronchitis exacerbation",
    "p. falciparum": "plasmodium falciparum malaria uncomplicated 1f40",
    "p.falciparum": "plasmodium falciparum malaria uncomplicated 1f40",
    "falciparum": "plasmodium falciparum malaria uncomplicated 1f40",
    "mrdt": "malaria rapid diagnostic test",
    "bs for mps": "blood slide malaria parasites",
    "mps": "malaria parasites",
    "al": "artemether lumefantrine antimalarial",
    "coartem": "artemether lumefantrine antimalarial",
    "panadol": "paracetamol analgesic antipyretic",
    "pcm": "paracetamol",
    "ors": "oral rehydration salts gastroenteritis diarrhea",
    "age": "acute gastroenteritis infectious diarrhea colitis",
    "ge": "gastroenteritis infectious diarrhea",
    "add": "acute diarrhoeal disease gastroenteritis",
    "sob": "shortness of breath dyspnoea breathless",
    "c/o": "complaining of",
    "dx": "diagnosis",
    "bp": "blood pressure hypertension",
    "htn": "hypertension essential high blood pressure",
    "dm": "diabetes mellitus hyperglycaemia",
    "t2dm": "type 2 diabetes mellitus",
    "t1dm": "type 1 diabetes mellitus",
    "cva": "cerebrovascular accident stroke",
    "rsv": "respiratory syncytial virus bronchiolitis",
    "gerd": "gastroesophageal reflux disease",
    "pud": "peptic ulcer disease gastric ulcer duodenal",
    "pid": "pelvic inflammatory disease",
    "sti": "sexually transmitted infection",
    "std": "sexually transmitted disease",
    "tinea capitis": "dermatophytosis scalp tinea fungal ringworm",
    "tinea corporis": "dermatophytosis body tinea fungal ringworm",
    "tinea pedis": "dermatophytosis foot athlete foot",
    "otitis media": "acute otitis media ear infection",
    "aom": "acute otitis media middle ear",
    "asthma attack": "asthma with acute exacerbation bronchospasm wheeze",
    "wheeze": "asthma acute exacerbation bronchospasm",
    "wheezing": "asthma acute exacerbation bronchospasm",
    "pneumonia": "pneumonia lung infection lower respiratory consolidation",
    "tonsillitis": "acute tonsillitis sore throat pharyngitis",
    "pharyngitis": "acute pharyngitis sore throat",
    "gastroenteritis": "infectious gastroenteritis colitis diarrhoea vomiting",
    "diarrhoea": "gastroenteritis infectious diarrhoea enteritis",
    "diarrhea": "gastroenteritis infectious diarrhoea enteritis"
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)?")

def tokenize(text: str, expand_abbreviations: bool = True) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens with clinical expansion."""
    if not text:
        return []
    
    text_lower = text.lower()
    extra_tokens = []
    
    if expand_abbreviations:
        for phrase, expansion in CLINICAL_ABBREVIATIONS.items():
            if phrase in text_lower:
                extra_tokens.extend(TOKEN_PATTERN.findall(expansion))
    
    tokens = TOKEN_PATTERN.findall(text_lower)
    if extra_tokens:
        tokens.extend(extra_tokens)
    return tokens


class BM25Okapi:
    """Fast, dependency-free BM25Okapi ranker."""
    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avg_doc_length = sum(self.doc_lengths) / max(1, self.corpus_size)
        
        self.df: Dict[str, int] = Counter()
        self.doc_term_freqs: List[Dict[str, int]] = []
        for doc in corpus:
            tf = Counter(doc)
            self.doc_term_freqs.append(tf)
            for term in tf:
                self.df[term] += 1
                
        self.idf: Dict[str, float] = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        scores = [0.0] * self.corpus_size
        k1 = self.k1
        b = self.b
        avg_dl = self.avg_doc_length

        for token in query_tokens:
            if token not in self.idf:
                continue
            idf_val = self.idf[token]
            for doc_idx in range(self.corpus_size):
                tf_map = self.doc_term_freqs[doc_idx]
                tf = tf_map.get(token, 0)
                if tf == 0:
                    continue
                dl = self.doc_lengths[doc_idx]
                numerator = tf * (k1 + 1.0)
                denominator = tf + k1 * (1.0 - b + b * (dl / avg_dl))
                scores[doc_idx] += idf_val * (numerator / denominator)
        return scores

    def top_k(self, query_tokens: List[str], k: int = 25) -> List[Tuple[int, float]]:
        scores = self.get_scores(query_tokens)
        scored_docs = [(idx, score) for idx, score in enumerate(scores) if score > 0]
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:k]
