import argparse
import os
from typing import List, Dict

from flask import Flask, request, jsonify

from dataset import DataSet
from model import TaggingModel


class PredictionHandler(object):

    def __init__(self, model_dir: str, fieldnames: List[str], padding: int=80, language: str="pl"):
        meta_path = os.path.join(model_dir, "meta.json")
        self.__model: TaggingModel = TaggingModel.load(model_dir)
        self.__data: DataSet = DataSet.empty(meta_path, fieldnames, padding)
        self.__language = language
        self.nlp = None

    def predict(self, data: List[List[Dict[str, str]]]) -> Dict[str, any]:
        input_data = self.__data.copy()
        input_data.set_data(data)
        result = self.__model.predict(input_data, string_labels=True, verbose=0)
        if isinstance(result, tuple): return {"tags": result[0], "labels": result[1]}
        else: return {"tags": result}

    def tokenize(self, data: List[str]) -> List[List[Dict[str, str]]]:
        if self.nlp is None:
            import spacy
            self.nlp = spacy.blank(self.__language)
        return [[{"value": str(tok)} for tok in self.nlp(sent)] for sent in data]

def create_app():
    app = Flask(__name__)
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=str, required=True)
    parser.add_argument("--padding", type=int, default=80)
    parser.add_argument("--fieldnames", type=str, default="value")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--gpu", type=str, default="0")
    parser.add_argument("--language", type=str, default="pl")
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    fieldnames = [fname.strip() for fname in args.fieldnames.split(sep=",")]
    server = PredictionHandler(args.model_dir, fieldnames, padding=args.padding, language=args.language)

    @app.route("/", methods=["POST"])
    def index() -> List[List[str]]:
        data: any = request.json
        sentences = data.get("sentences")
        tokenize: bool = data.get("tokenize")
        if tokenize:
            sentences = server.tokenize(sentences)
        res = server.predict(sentences)
        return jsonify(res)

    return app, args


if __name__ == '__main__':
    app, args = create_app()
    app.run(host=args.host, port=args.port, threaded=False)
