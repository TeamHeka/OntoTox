import re, os, time, csv, sys, yaml
from quickumls import QuickUMLS
import pandas as pd
from owlready2 import *
from utils_functions import *

from pymedextcore.annotators import Annotation, Annotator, Relation
from pymedextcore.document import Document

with open("config.yml", "r") as ymlfile:
    cfg = yaml.safe_load(ymlfile)

sys.path.append(cfg["pymedext_dir"])
from utils import rawtext_loader
from annotators import Endlines, SentenceTokenizer, Hypothesis, \
                                    ATCDFamille, SyntagmeTokenizer, Negation, RegexMatcher, \
                                    Pipeline, SectionSplitter
from annotatorsTox import QuickUMLSAnnotator,TableLineExtractor , ToxTableDetector, ToxTableLineExtractor


def main(argv=None):
    
    try:
        data_qst = argv[argv.index("--data") + 1]
    except ValueError:
        try:
            data_qst = argv[argv.index("-d") + 1]
        except ValueError:
            data_qst = cfg["data"]["QST"]
    
    try:
        path_owl = argv[argv.index("--pathOut") + 1]
    except ValueError:
        try:
            path_owl = argv[argv.index("-p") + 1]
        except ValueError:
            path_owl = cfg["outputs"]["owl_files"]
            
    try:
        name_owl_in = argv[argv.index("--fileNameIn") + 1]
    except ValueError:
        try:
            name_owl_in = argv[argv.index("-fi") + 1]
        except ValueError:
            name_owl_in = "OntoTox_FT_tables.owl"
                        
    try:
        quickumls_fp = argv[argv.index("--QuickUMLS") + 1]
    except ValueError:
        try:
            quickumls_fp = argv[argv.index("-qu") + 1]
        except ValueError:
            quickumls_fp = cfg["quickumls"]
    
    try:
        regex_grade_file = argv[argv.index("--regexGrade") + 1]
    except ValueError:
        try:
            regex_grade_file = argv[argv.index("-rg") + 1]
        except ValueError:
            regex_grade_file = cfg["regex_grade"]

    qst_df = pd.read_csv(filepath_or_buffer = data_qst, sep= ";")
    qst_name_char = pd.read_csv(filepath_or_buffer=cfg["data"]["qst_metadata"], sep= ";")
    
    qst_df["TYPE"] = "PROCHE"
    qst_df = qst_df[["CONCEPT_CD","START_DATE", "PATIENT_NUM", "TVAL_CHAR", "TYPE"]]
    
    quickumls_fp_2 = quickumls_fp
    matcher = QuickUMLS(quickumls_fp_2)
    
    qst_name_char["QuickUMLS"] = qst_name_char.apply(lambda row :  matcher.match(row.NAME_CHAR, best_match=True, ignore_syntax=False), axis = 1)
    qst_name_char[qst_name_char['QuickUMLS'].str.len() == 0].filter(["NAME_CHAR"]).drop_duplicates()
    
    qst_df=qst_df.merge(qst_name_char, how='left', on='CONCEPT_CD')
    
    qst_df = qst_df[qst_df.TVAL_CHAR.str.contains("[Gg][Rr][Aa][Dd][Ee]\\s*[0-5]*[I|V]*|[Gg]\\s*([[0-5]|(III|IV|II|I|V))", regex=True)== True ]
    
    qst_df["GRADE_NUM"] = qst_df.apply(lambda row :  returns_norm_num_grade2(row.TVAL_CHAR)[1], axis = 1)
    qst_df = qst_df[qst_df['QuickUMLS'].str.len() != 0]
    
    # to_onto
    onto =  get_ontology(path_owl + name_owl_in).load()
    with onto :
        class QST_answer(PROVO.Entity): pass
        class ProcessQST(PROVO.Agent): pass
        timestr = time.strftime("%Y%m%d-%H%M%S")
        name_process = "process_qst" + timestr
        processClass = types.new_class(name_process, (PROVO.Activity,))
        PROVO.wasAssociatedWith[processClass].append(ProcessQST)
        
    for i in qst_df.index :
        qst_grade_df_to_onto(df_line = qst_df.loc[i], onto = onto, dict_class_grade = dict_class_grade, index = i, processClass= processClass)
    
    name_owl = name_owl_in.replace(".owl", "") + "_qst.owl"    
    onto.save(path_owl + name_owl) 
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))