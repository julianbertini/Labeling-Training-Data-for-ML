import spacy
import yaml
import os.path
from spacy.pipeline import EntityRuler
from itertools import chain, combinations


# TODO:
#   A general problem is that names are usually not unique, so if the database      finds more than one person that matches the given name, how does it decide      which one to go with?

# NOTE: The Person record stores firstName and lastName attributes. So will probably have to combine them into one string to compare with the single name entity found here.

def open_filebase():
    people = []
    with open("filebase.yaml","r") as extensions:
        try:
            defaultListsDict = yaml.safe_load(extensions)
            peeps = defaultListsDict['Persons']
            people = [ext for ext in peeps]
        except Exception as ex:
            print("Error processing file: " + ex)

    return people

def check_noun_chunks(doc, ent, people, noun_chunks, ruler):
    # chunk is a SpaCy Span object
    # noun chunks are each noun phrase in the sentence. It basically breaks apart primary nouns in the sentence.

    for chunk in noun_chunks:
        if ent.start >= chunk.start and ent.end <= chunk.end:
            # then we know we are at the token's noun chunk

            # first make sure SpaCy considers everything in the noun chunk a PROPN or NOUN. Take out all other words.
            span = chunk
            for i in range(chunk.start, chunk.end):
                if doc[i].pos_ == "PROPN" or doc[i].pos_ == "NOUN":
                    break
                else:
                    span = doc[i+1:chunk.end]

            # If the resulting span is the same as the ent, then we know SpaCy has correctly labeled the full entity.
            if span.start == ent.start and span.end == ent.end:
                break

            # Check span against "filebase"
            # This isn't quite the powerset, and I think this is O(n) time
            for i in range(len(span)):
                for j in range(i,len(span)):
                    test_ent_str = doc.text[span[i].idx:span[j].idx+len(span[j].text)]
                    # Here test against filebase
                    if test_ent_str in people:
                        print("***FOUND UNDT: " + test_ent_str)
                        # Add it to the EntityRuler
                        ruler.add_patterns([{"label": "PERSON", "pattern": test_ent_str}])
                        # Save the ruler with the new rule
                        ruler.to_disk("rules.jsonl")
                        break


# TODO: so one tricky thing here is the punctuation (or more specifically, brackets or parenthesis). In the case of CH (COL) James Palmer, the punctuation in the name throws off this scheme. We can test things with punctuation and see how that goes?
def grab_neighbor(doc, span):
    if span.start == 0:
        left = doc[span.start]
    else:
        left = doc[span.start-1]
    if span.end == len(doc):
        right = doc[span.end-1]
    else:
        right = doc[span.end]

    if ( (left.pos_ != "NOUN" and left.pos_ != "PROPN" and not left.is_bracket and not left.is_punct) or left.i <= 0) and ( (right.pos_ != "NOUN" and right.pos_ != "PROPN" and not right.is_bracket and not right.is_punct) or right.i == len(doc)-1 ):
        return span

    if (right.i < len(doc)-1):
        if ( (left.pos_ != "NOUN" and left.pos_ != "PROPN" and not left.is_bracket and not left.is_punct) or left.i == 0 ) and (right.pos_ == "NOUN" or right.pos_ == "PROPN" or right.is_bracket or right.is_punct):
            return grab_neighbor(doc, doc[span.start:span.end+1])

    if (left.i > 0):
        if (left.pos_ == "NOUN" or left.pos_ == "PROPN" or left.is_bracket or left.is_punct) and ( (right.pos_ != "NOUN" and right.pos_ != "PROPN" and not right.is_bracket and not right.is_punct) or right.i==len(doc)-1 ):
            return grab_neighbor(doc, doc[span.start-1:span.end])

    if (right.i < len(doc)-1 and left.i > 0):
        return grab_neighbor(doc, doc[span.start-1:span.start+1])


# Do the same process as with noun_chunks but manually by just looking at NOUN and PROPN sequence of tags around some entity.
def check_neighbors(doc, ent, ruler, people):

    # Index into the tokens that are next to the boundaries of the span entity and grab the entire noun/propn sequence
    span = grab_neighbor(doc, ent)
    span_text = doc.text[doc[span.start].idx:doc[span.end-1].idx+len(doc[span.end-1].text)]
    # If we already have the entire entity
    if span.start == ent.start and span.end == ent.end:
        return ruler
    if (span_text in [pattern["pattern"] for pattern in ruler.patterns]):
        return ruler

    # Check span against "filebase"
    # This isn't quite the powerset, and I think this is O(n) time
    for i in range(len(span)):
        for j in range(i,len(span)):
            test_ent_str = doc.text[span[i].idx:span[j].idx+len(span[j].text)]
            # Here test against filebase
            if test_ent_str in people:
                print("***DISCOVERED: " + test_ent_str)
                # Add it to the EntityRuler
                ruler.add_patterns([{"label": "PERSON", "pattern": test_ent_str}])
                # Save the ruler with the new rule
                return ruler
    return ruler

def main():

    people = open_filebase()

    nlp = spacy.load("en_core_web_md")
    text = "Let me tell you about a story, which involves Mr. Jack Sparrow and TRADOC Command Chaplain and CH (COL) James Palmer. It was a Boeing 777. And MAJ Freketic. Then we saw Mayor Julian Bertini III. How about Julian Bertini. But I also want to include TRADOC as an org."
    # text = "It was late at night when TRADOC Command Chaplain arrived."

    ruler = EntityRuler(nlp, overwrite_ents=True)
    if os.path.isfile("rules.jsonl"):
        ruler.from_disk("rules.jsonl")
    saved_patterns = len(ruler.patterns)
    nlp.add_pipe(ruler)

    doc = nlp(text)
    noun_chunks = list(doc.noun_chunks)

    for ent in doc.ents: # ent is a span

        if ent.label_ == "PERSON": # try checking to see if NER is correct
            # check the text of the entity against the filebase
            if doc.text[doc[ent.start].idx:doc[ent.end-1].idx+len(doc[ent.end-1].text)] in people:
                print("***FOUND: " + doc.text[doc[ent.start].idx:doc[ent.end-1].idx+len(doc[ent.end-1].text)])
            else:
                ruler = check_neighbors(doc, ent, ruler, people)
        else:
            ruler = check_neighbors(doc, ent, ruler, people)

    if len(ruler.patterns) > saved_patterns:
        if os.path.isfile("rules.jsonl"):
            os.remove("rules.jsonl")
        ruler.to_disk("rules.jsonl")


    # print(list(doc.noun_chunks))

    # ruler.add_patterns(
    #     [{"label": "PERSON", "pattern": "CH (COL) James Palmer"}, {"label": "PRODUCT", "pattern": "Boeing 777"}])
    # nlp.add_pipe(ruler)

    # ruler.to_disk("rules.jsonl")

    # ruler = ruler.from_disk("rules.jsonl")

    # for token in doc:
    #     print(token.text + ": " + token.ent_type_ + ": " + token.ent_iob_ + ": " + token.pos_)

    # ents = list(doc.ents)
    # for ent in doc.ents:
    #     print(ent)


if __name__ == "__main__":
    main()