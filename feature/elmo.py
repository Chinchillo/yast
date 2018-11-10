import os
from typing import Any

import numpy as np
from keras import Input
from keras.layers import Lambda

from bilm import Batcher
from dataset import DataSet
from feature.base import Feature


class ELMoEmbeddingFeature(Feature):

    def __init__(self, name: str, empedding_dir: str, padding: int=80):
        self.__name = name
        self.__padding = padding
        self.__embedding_dir = empedding_dir
        self.__batcher = self.__create_batcher(empedding_dir)

    def input(self):
        return Input(shape=(None,50),dtype=np.int32,name=self.__name + '_elmo_embedding_input')

    def model(self, input: Any):
        options_file: str = os.path.join(self.__embedding_dir, "options.json")
        weight_file: str = os.path.join(self.__embedding_dir, "weights.hdf5")
        def __lambda_layer(x):
            import tensorflow as tf
            from bilm import BidirectionalLanguageModel, weight_layers
            x_input = tf.cast(x, tf.int32)
            with tf.variable_scope('', reuse=tf.AUTO_REUSE):
                bilm = BidirectionalLanguageModel(options_file, weight_file)
                embedding_op = bilm(x_input)
                context_input = weight_layers('input', embedding_op, l2_coef=0.0)
                return context_input['weighted_op']
        return Lambda(__lambda_layer, name=self.__name + '_elmo_lambda_layer')(input)

    def __create_batcher(self, embedding_dir: str) -> Batcher:
        vocab_path: str = os.path.join(embedding_dir, "vocabulary.txt")
        return Batcher(vocab_path, 50)

    def name(self) -> str:
        return self.__name

    def transform(self, dataset: DataSet):
        text = []
        for sent in dataset.data:
            sent_text = []
            for word_idx, word in enumerate(sent):
                if word_idx >= dataset.sentence_length(): break
                sent_text.append(word[self.__name])
            text.append(sent_text)
        return self.__batcher.batch_sentences(text)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["_ELMoEmbeddingFeature__batcher"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__batcher = self.__create_batcher(self.__embedding_dir)