class EntityWrapper():

    def __init__(self, doc, ent):
        self.start = doc[ent.start].idx
        self.end = doc[ent.end-1].idx+len(doc[ent.end-1].text)
        self.text = doc.text[doc[ent.start].idx:doc[ent.end-1].idx+len(doc                  [ent.end-1].text)]
        self.label = ent.label_
        if not self.label:
            self.label = ORG
        self.root = ent