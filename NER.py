import spacy
import yaml
import os.path
from spacy.pipeline import EntityRuler
from .entity_wrapper import EntityWrapper

ORG = "ORG"
PERSON = "PERSON"
GPE = "GPE"

# TODO:
#   A general problem is that names are usually not unique, so if the database      finds more than one person that matches the given name, how does it decide      which one to go with?

#   With mil.Unit, it collides with org.Organization. Maybe in this case, we        just test against the databse to see if it is an org or a unit, and             whichever suceeeds we go along with.

#   SpaCy does not recognize 9006th Air Mobility Squadron at all. It does           label them as PROPN, though. This can be used to add it to EntityRuler.
#       JK it does catch part of it sometimes


class NER():

    def __init__(self):
        self.text = "It was late at night when the TRADOC Command Chaplain arrived. We were in Asheville NC, where the night was cold. Then the 899 CPT unit showed up. And then the 9006th Air Mobility Squadron flew over the water in their jets. It was NATO who said that was a good idea. Anyways, it was general Mckeiver from the USAFRICOM who recommended we move forward, but the FBI did not like that."
        self.entities = None

    def executeNER(self):
        ents_temp = []
        orgs = self.open_filebase()

        nlp = spacy.load("en_core_web_md")

        # text = "Is it F.B.I or FBI? The UN would say otherwise. NATO is also cool. What about units? What will it think USEUCOM is? What about Army? What about 899 CPT? What about the 9006th Air Mobility Squadron? It was a Boeing 777? Then we went to Northwest Africa. then we went to Fort Gordon, GA. What about United States Army Forces Command."

        # is_punct but not a period.

        # text = "Let me tell you about a story, which involves Capitan Jack Sparrow and TRADOC Command Chaplain and CH (COL) James Palmer. It was a Boeing 777. And MAJ Freketic. Then we saw Mayor Julian Bertini III. How about Julian Bertini."

        ruler = EntityRuler(nlp, overwrite_ents=True)
        if os.path.isfile("rules.jsonl"):
            ruler.from_disk("rules.jsonl")
        saved_patterns = len(ruler.patterns)
        nlp.add_pipe(ruler, name="loaded_ruler")

        doc = nlp(self.text)

        # ent is a span
        for ent in doc.ents:
            new_ent = self.grab_neighbor(doc,ent)
            if new_ent not in ents_temp:
                ents_temp.append(new_ent)

        self.entities = [EntityWrapper(doc, ent) for ent in ents_temp]

        # print (len(ruler.patterns))
        # if len(ruler.patterns) > saved_patterns:
        #     if os.path.isfile("rules.jsonl"):
        #         os.remove("rules.jsonl")
        #     ruler.to_disk("rules.jsonl")

    def open_filebase(self):
        orgs = []
        with open("/Users/julian.bertini/julianbertini/twosix/spsacy/labeling_data/filebase.yaml","r") as filebase:
            try:
                defaultListsDict = yaml.safe_load(filebase)
                orgs = defaultListsDict['ORGs']
                if not orgs:
                    orgs = []
            except Exception as ex:
                print("Error processing file: " + ex)

        return orgs

    def write_filebase(self, data):
        with open("filebase.yaml","w") as filebase:
            yaml.dump(data, filebase)
            print(yaml.dump(data))

    def grab_neighbor(self, doc, span):
        if span.start == 0:
            left = doc[span.start]
        else:
            left = doc[span.start-1]
        if span.end == len(doc):
            right = doc[span.end-1]
        else:
            right = doc[span.end]

        if ( (left.pos_ != "NOUN" and left.pos_ != "PROPN" and not left.is_bracket and left.pos_ != "NUM") or left.i <= 0) and ( (right.pos_ != "NOUN" and right.pos_ != "PROPN" and not right.is_bracket and right.pos_ != "NUM") or right.i == len(doc)-1 ):
            return span

        if (right.i < len(doc)-1):
            if ( (left.pos_ != "NOUN" and left.pos_ != "PROPN" and not left.is_bracket and left.pos_ != "NUM") or left.i == 0 ) and (right.pos_ == "NOUN" or right.pos_ == "PROPN" or right.is_bracket or right.pos_ == "NUM"):
                return self.grab_neighbor(doc, doc[span.start:span.end+1])

        if (left.i > 0):
            if (left.pos_ == "NOUN" or left.pos_ == "PROPN" or left.is_bracket or left.pos_ == "NUM") and ( (right.pos_ != "NOUN" and right.pos_ != "PROPN" and not right.is_bracket and right.pos_ != "NUM") or right.i==len(doc)-1 ):
                return self.grab_neighbor(doc, doc[span.start-1:span.end])

        if (right.i < len(doc)-1 and left.i > 0):
            return self.grab_neighbor(doc, doc[span.start-1:span.start+1])


    # Do the same process as with noun_chunks but manually by just looking at NOUN and PROPN sequence of tags around some entity.
    def check_neighbors(self, doc, ent, ruler, orgs):

        # Index into the tokens that are next to the boundaries of the span entity and grab the entire noun/propn sequence
        span = self.grab_neighbor(doc, ent)
        span_text = doc.text[doc[span.start].idx:doc[span.end-1].idx+len(doc[span.end-1].text)]
        # If we already have the entire entity
        if span.start == ent.start and span.end == ent.end:
            return ruler
        if span_text in [pattern["pattern"] for pattern in ruler.patterns]:
            return ruler

        # Check span against "filebase"
        # This isn't quite the powerset, and I think this is O(n) time
        for i in range(len(span)):
            for j in range(i,len(span)):
                test_ent_str = doc.text[span[i].idx:span[j].idx+len(span[j].text)]

                # Here test against filebase
                if test_ent_str in orgs and test_ent_str not in [pattern            ["pattern"] for pattern in ruler.patterns]: # Orgs

                    print("***DISCOVERED ORG: " + test_ent_str)

                    # Add it to the EntityRuler
                    ruler.add_patterns([{"label": "ORG", "pattern": test_ent_str}])

                    # Add it to the filebase
                    data = {"ORGs":test_ent_str}
                    self.write_filebase(data)

                    # Save the ruler with the new rule
                    return ruler

        return ruler


# print(list(doc.noun_chunks))

# ruler.add_patterns(
#     [{"label": "PERSON", "pattern": "CH (COL) James Palmer"}, {"label": "PRODUCT", "pattern": "Boeing 777"}])
# nlp.add_pipe(ruler)

# for token in doc:
#     print(token.text + ": " + token.ent_type_ + ": " + token.ent_iob_ + ": " + token.pos_)

# ents = list(doc.ents)
# for ent in doc.ents:
#     print(ent)