#!/usr/bin/env python3
"""Emit data/curated/books.json: the 66-book canon table.

`composed` gives a conventional critical dating range (negative = BCE) for the
book reaching roughly its present form. These are scholarly estimates, widely
contested, and are used only to position books on the composition timeline.
"""
import json, pathlib

# osis, name, chapters, testament, division, composed_start, composed_end
ROWS = [
 ("Gen","Genesis",50,"OT","Torah",-950,-450),
 ("Exod","Exodus",40,"OT","Torah",-950,-450),
 ("Lev","Leviticus",27,"OT","Torah",-700,-450),
 ("Num","Numbers",36,"OT","Torah",-700,-450),
 ("Deut","Deuteronomy",34,"OT","Torah",-700,-550),
 ("Josh","Joshua",24,"OT","History",-650,-550),
 ("Judg","Judges",21,"OT","History",-650,-550),
 ("Ruth","Ruth",4,"OT","History",-550,-400),
 ("1Sam","1 Samuel",31,"OT","History",-630,-540),
 ("2Sam","2 Samuel",24,"OT","History",-630,-540),
 ("1Kgs","1 Kings",22,"OT","History",-620,-540),
 ("2Kgs","2 Kings",25,"OT","History",-620,-540),
 ("1Chr","1 Chronicles",29,"OT","History",-400,-300),
 ("2Chr","2 Chronicles",36,"OT","History",-400,-300),
 ("Ezra","Ezra",10,"OT","History",-400,-300),
 ("Neh","Nehemiah",13,"OT","History",-400,-300),
 ("Esth","Esther",10,"OT","History",-400,-300),
 ("Job","Job",42,"OT","Wisdom",-600,-400),
 ("Ps","Psalms",150,"OT","Wisdom",-1000,-300),
 ("Prov","Proverbs",31,"OT","Wisdom",-700,-300),
 ("Eccl","Ecclesiastes",12,"OT","Wisdom",-350,-200),
 ("Song","Song of Solomon",8,"OT","Wisdom",-500,-300),
 ("Isa","Isaiah",66,"OT","Major Prophets",-740,-500),
 ("Jer","Jeremiah",52,"OT","Major Prophets",-626,-560),
 ("Lam","Lamentations",5,"OT","Major Prophets",-586,-540),
 ("Ezek","Ezekiel",48,"OT","Major Prophets",-593,-560),
 ("Dan","Daniel",12,"OT","Major Prophets",-250,-164),
 ("Hos","Hosea",14,"OT","Minor Prophets",-750,-700),
 ("Joel","Joel",3,"OT","Minor Prophets",-450,-350),
 ("Amos","Amos",9,"OT","Minor Prophets",-760,-740),
 ("Obad","Obadiah",1,"OT","Minor Prophets",-586,-550),
 ("Jonah","Jonah",4,"OT","Minor Prophets",-450,-350),
 ("Mic","Micah",7,"OT","Minor Prophets",-737,-690),
 ("Nah","Nahum",3,"OT","Minor Prophets",-663,-612),
 ("Hab","Habakkuk",3,"OT","Minor Prophets",-640,-598),
 ("Zeph","Zephaniah",3,"OT","Minor Prophets",-640,-609),
 ("Hag","Haggai",2,"OT","Minor Prophets",-520,-515),
 ("Zech","Zechariah",14,"OT","Minor Prophets",-520,-480),
 ("Mal","Malachi",4,"OT","Minor Prophets",-460,-430),
 ("Matt","Matthew",28,"NT","Gospels",70,90),
 ("Mark","Mark",16,"NT","Gospels",66,72),
 ("Luke","Luke",24,"NT","Gospels",80,95),
 ("John","John",21,"NT","Gospels",90,110),
 ("Acts","Acts",28,"NT","Acts",80,95),
 ("Rom","Romans",16,"NT","Pauline",55,58),
 ("1Cor","1 Corinthians",16,"NT","Pauline",53,55),
 ("2Cor","2 Corinthians",13,"NT","Pauline",55,57),
 ("Gal","Galatians",6,"NT","Pauline",48,55),
 ("Eph","Ephesians",6,"NT","Pauline",60,90),
 ("Phil","Philippians",4,"NT","Pauline",57,62),
 ("Col","Colossians",4,"NT","Pauline",57,80),
 ("1Thess","1 Thessalonians",5,"NT","Pauline",49,52),
 ("2Thess","2 Thessalonians",3,"NT","Pauline",50,90),
 ("1Tim","1 Timothy",6,"NT","Pauline",90,110),
 ("2Tim","2 Timothy",4,"NT","Pauline",90,110),
 ("Titus","Titus",3,"NT","Pauline",90,110),
 ("Phlm","Philemon",1,"NT","Pauline",57,62),
 ("Heb","Hebrews",13,"NT","General",60,95),
 ("Jas","James",5,"NT","General",50,90),
 ("1Pet","1 Peter",5,"NT","General",65,90),
 ("2Pet","2 Peter",3,"NT","General",100,130),
 ("1John","1 John",5,"NT","General",90,110),
 ("2John","2 John",1,"NT","General",90,110),
 ("3John","3 John",1,"NT","General",90,110),
 ("Jude","Jude",1,"NT","General",90,110),
 ("Rev","Revelation",22,"NT","Apocalyptic",90,96),
]

def main():
    books = [
        {
            "i": i,
            "osis": osis,
            "name": name,
            "chapters": ch,
            "testament": t,
            "division": div,
            "composed": [a, b],
        }
        for i, (osis, name, ch, t, div, a, b) in enumerate(ROWS)
    ]
    out = pathlib.Path("data/curated/books.json")
    out.write_text(json.dumps(books, indent=1) + "\n")
    print(f"wrote {out} ({len(books)} books, {sum(b['chapters'] for b in books)} chapters)")

if __name__ == "__main__":
    main()
