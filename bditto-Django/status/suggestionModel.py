
import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_hub as hub
from scipy.spatial.distance import cosine

module_url = "https://tfhub.dev/google/universal-sentence-encoder/4" 
suggsModel = hub.load(module_url)
