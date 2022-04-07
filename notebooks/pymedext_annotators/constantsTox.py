from collections import OrderedDict


FIRST_CELL_DICT = {
    'ADE' : ["effet(s{0,1})",
            "tox"]
    }

TYPE_TABLE_DICT = {
    'ADE' : 
        { 
        '1' : ["effet(s{0,1})\\s+ind[eéè]sirable(s{0,1})",
               "effet(s{0,1})\\s+secondaire(s{0,1})" ],
        '2' : ["grade(s{0,1}).{0,10}"],
        '3': ["date\\s+d[ée]but.{0,10}"],
        '4' : ["date\\s+fin.{0,10}"],
        '5' : ["li[ée]\\s+au.{0,20}"]
        }
    }