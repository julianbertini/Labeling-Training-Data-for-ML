import spacy
import yaml
import os.path
from spacy.pipeline import EntityRuler
from itertools import chain, combinations


# TODO:
#   A general problem is that names are usually not unique, so if the database      finds more than one person that matches the given name, how does it decide      which one to go with?

#   With mil.Unit, it collides with org.Organization. Maybe in this case, we        just test against the databse to see if it is an org or a unit, and             whichever suceeeds we go along with.

#    SpaCy does not recognize 9006th Air Mobility Squadron at all. It does           label them as PROPN, though. This can be used to add it to EntityRuler.
#        JK it does catch part of it sometimes

def open_filebase():
    orgs = []
    with open("filebase.yaml","r") as extensions:
        try:
            defaultListsDict = yaml.safe_load(extensions)
            orgs = defaultListsDict['Orgs']
            units = defaultListsDict['Units']
        except Exception as ex:
            print("Error processing file: " + ex)

    return orgs, units

def grab_neighbor(doc, span):
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
            return grab_neighbor(doc, doc[span.start:span.end+1])

    if (left.i > 0):
        if (left.pos_ == "NOUN" or left.pos_ == "PROPN" or left.is_bracket or left.pos_ == "NUM") and ( (right.pos_ != "NOUN" and right.pos_ != "PROPN" and not right.is_bracket and right.pos_ != "NUM") or right.i==len(doc)-1 ):
            return grab_neighbor(doc, doc[span.start-1:span.end])

    if (right.i < len(doc)-1 and left.i > 0):
        return grab_neighbor(doc, doc[span.start-1:span.start+1])


# Do the same process as with noun_chunks but manually by just looking at NOUN and PROPN sequence of tags around some entity.
def check_neighbors(doc, ent, ruler, data):

    # Index into the tokens that are next to the boundaries of the span entity and grab the entire noun/propn sequence
    span = grab_neighbor(doc, ent)
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
            if test_ent_str in data[0] and test_ent_str not in [pattern            ["pattern"] for pattern in ruler.patterns]: # Orgs

                print("***DISCOVERED ORG: " + test_ent_str)
                # Add it to the EntityRuler
                ruler.add_patterns([{"label": "ORG", "pattern": test_ent_str}])
                # Save the ruler with the new rule
                return ruler
            if test_ent_str in data[1] and test_ent_str not in [pattern            ["pattern"] for pattern in ruler.patterns]: # Units

                print("***DISCOVERED UNIT: " + test_ent_str)
                # Add it to the EntityRuler. Units are also ORG for now.
                ruler.add_patterns([{"label": "ORG", "pattern": test_ent_str}])
                # Save the ruler with the new rule
                return ruler

    return ruler


def main():

    orgs, units = open_filebase()

    nlp = spacy.load("en_core_web_md")

    # text = "Is it F.B.I or FBI? The UN would say otherwise. NATO is also cool. What about units? What will it think USEUCOM is? What about Army? What about 899 CPT? What about the 9006th Air Mobility Squadron? It was a Boeing 777? Then we went to Northwest Africa. then we went to Fort Gordon, GA. What about United States Army Forces Command."

    # is_punct but not a period.

    text = "It was late at night when the TRADOC Command Chaplain arrived. We were in Asheville NC, where the night was cold. Then the 899 CPT unit showed up. And then the 9006th Air Mobility Squadron flew over the water in their jets. It was NATO who said that was a good idea. Anyways, it was general Mckeiver from the USAFRICOM who recommended we move forward, but the FBI did not like that."
    # text = "Let me tell you about a story, which involves Capitan Jack Sparrow and TRADOC Command Chaplain and CH (COL) James Palmer. It was a Boeing 777. And MAJ Freketic. Then we saw Mayor Julian Bertini III. How about Julian Bertini."

    ruler = EntityRuler(nlp, overwrite_ents=True)
    if os.path.isfile("rules_orgs.jsonl"):
        ruler.from_disk("rules_orgs.jsonl")
    saved_patterns = len(ruler.patterns)
    nlp.add_pipe(ruler, name="loaded_ruler")

    doc = nlp(text)
    # noun_chunks = list(doc.noun_chunks)

    for ent in doc.ents: # ent is a span

        if ent.label_ == "ORG": # try checking to see if NER is correct
            # check the text of the entity against the filebase
            ent_text = doc.text[doc[ent.start].idx:doc[ent.end-1].idx+len(doc               [ent.end-1].text)]

            if ent_text in orgs:
                print("***FOUND ORG: " + ent_text)
            elif ent_text in units:
                print("***FOUND UNIT: " + ent_text)
            else:
                ruler = check_neighbors(doc, ent, ruler, (orgs,units))
        else:
            ruler = check_neighbors(doc, ent, ruler, (orgs,units))

    if len(ruler.patterns) > saved_patterns:
        if os.path.isfile("rules_orgs.jsonl"):
            os.remove("rules_orgs.jsonl")
        ruler.to_disk("rules_orgs.jsonl")


    # print(list(doc.noun_chunks))

    # ruler.add_patterns(
    #     [{"label": "PERSON", "pattern": "CH (COL) James Palmer"}, {"label": "PRODUCT", "pattern": "Boeing 777"}])
    # nlp.add_pipe(ruler)

    # for token in doc:
    #     print(token.text + ": " + token.ent_type_ + ": " + token.ent_iob_ + ": " + token.pos_)

    ents = list(doc.ents)
    for ent in doc.ents:
        print(ent)


if __name__ == "__main__":
    main()