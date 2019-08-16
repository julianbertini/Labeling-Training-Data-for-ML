import json
import yaml
from flask import Flask
from flask import render_template
from flask import request

from .NER import NER
from .entity import Entity

app = Flask(__name__)
ner = NER()
training_set = {}


@app.route("/")
def test():
    return render_template('index.html')

@app.route("/getEntities")
def getEntities():
    ents_array = []

    if ner.entities:
        for ent in ner.entities:
            ents_array.append({
            "name": ent.text,
            "label": ent.label,
            "start": ent.start,
            "end": ent.end
            })
    else:
        ner.executeNER()
        for ent in ner.entities:
            ents_array.append({
            "name": ent.text,
            "label": ent.label,
            "start": ent.start,
            "end": ent.end
            })

    return json.dumps(ents_array)

@app.route("/getText")
def getText():
    return ner.text

#
# TODO: need to add a check so that no two entities with the same start and end # can exist
#
#
#
#
@app.route("/saveEntity")
def saveEntity():
    ent_start = request.args.get('start')
    ent_end = request.args.get('end')
    ent_label = request.args.get('label')
    new_ent = (ent_label, ent_start, ent_end)

    if new_ent not in training_set.setdefault(ner.text, []):
        training_set[ner.text].append(new_ent)

    return json.dumps(training_set)


# Here add to a JSON file, a dict where key is text and value is the entitySet
@app.route("/saveToDisk")
def saveEntitySet():

    with open('training_set.json', 'r') as file:
        try:
            stored_training_set = json.load(file)
        except Exception as ex:
            return "Error while opening training data JSON: " + str(ex)

    with open('training_set.json', 'w') as file:
        try:
            stored_training_set.update(training_set)
            json.dump(stored_training_set, file)
            return "Success"
        except Exception as ex:
            return "Error writing training data to JSON: " + str(ex)
