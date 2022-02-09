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
        data_tables = argv[argv.index("--data") + 1]
    except ValueError:
        try:
            data_tables = argv[argv.index("-d") + 1]
        except ValueError:
            data_tables = cfg["data"]["tables"]
    
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
            name_owl_in = "OntoTox_FT.owl"
                        
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

    tables_df = pd.read_csv(data_tables, header = None, sep = "|")    
    colomn_name = {0 : "SMALL_LOCATION_CD", 1 : "NUM_TABLE", 2 :"TABLE", 3 :"EXTRACTION_DATE"}
    tables_df = tables_df.rename(columns = colomn_name, inplace = False)
    tables_df["LOCATION_CD"] = tables_df.apply(lambda row : gives_LOCATION_CD(row.SMALL_LOCATION_CD), axis = 1 )
    tables_df = tables_df.dropna()
    tables_df["pymedext_doc"] = tables_df.apply(lambda row : Document(raw_text = str(row.TABLE)+">", ID = row.LOCATION_CD), axis = 1 )

    toxtabledetection = ToxTableDetector(['raw_text'], 'toxtable_detect', 'toxtable_detect:v1')
    linestableextraction = ToxTableLineExtractor(['toxtable_detect'], 'table_line', 'table_line:v1')
    pipeline = Pipeline(pipeline = [toxtabledetection, linestableextraction])
    tables_df["annotated_doc"] = tables_df.apply(lambda row : pipeline.annotate([row.pymedext_doc]), axis = 1 )

   
    
    tables_df["annotated_Documents"]= tables_df.apply(lambda row : returns_Documents_list(row.annotated_doc), axis = 1 )
    tables_df["tox_table_bool"] = tables_df.apply(lambda row : keeps_tox_tables(row.annotated_Documents), axis = 1 )
    tox_tables_df = tables_df[tables_df["tox_table_bool"] == "ADE"]
    
    ## Quickumls
    quickumls_fp_2=cfg["quickumls"]
    matcher = QuickUMLS(quickumls_fp_2)
    
    for i in tox_tables_df.index :
        QuickUML_to_list_of_doc(tox_tables_df.loc[i], matcher)
    
    onto =  get_ontology(path_owl + name_owl_in).load()
    ## to_onto
    dict_doc_to_date = doc_to_date(path = cfg["data"]["reports_metadata"])
    dict_doc_to_pat = doc_to_pat(path = cfg["data"]["reports_metadata"])
    with onto :
        class Tables(PROVO.Entity): pass
        class ProcessTables(PROVO.Agent): pass
        timestr = time.strftime("%Y%m%d-%H%M%S")
        name_process = "process_tables" + timestr
        processClass = types.new_class(name_process, (PROVO.Activity,))
        PROVO.wasAssociatedWith[processClass].append(ProcessTables)
    for i in tox_tables_df.index :
        table_df_to_onto(df_line = tox_tables_df.loc[i], onto = onto, dict_class_grade = dict_class_grade, index = i, processClass = processClass, dict_doc_to_date = dict_doc_to_date, dict_doc_to_pat = dict_doc_to_pat)
    
    name_owl = name_owl_in.replace(".owl", "") + "_tables.owl"    
    onto.save(path_owl + name_owl) 
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))