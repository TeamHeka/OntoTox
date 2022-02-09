import os, csv, re, sys, yaml
import pandas as pd
from owlready2 import *
from quickumls import QuickUMLS

from pymedextcore.annotators import Annotation, Annotator, Relation
from pymedextcore.document import Document

with open("config.yml", "r") as ymlfile:
    cfg = yaml.safe_load(ymlfile)

path_owl_db = cfg["owlready_db"]
default_world.set_backend(filename = path_owl_db, exclusive=False)
PYM = get_ontology("http://PYM/").load()
UMLS_CONCEPT = PYM["CUI"]
MDR = PYM["MDR"]
PROVO = get_ontology(cfg["provo"]).load()

dict_class_grade = {'0': 'Grade0',
                  '1': 'Grade1',
                  '2': 'Grade2',
                  '3': 'Grade3',
                  '4': 'Grade4',
                  '5': 'Grade5',
                  'null':'GradeNull'}

def owl_transcode_cui_to_meddra(CUI_ID) :
    if len(list(UMLS_CONCEPT[CUI_ID] >> MDR)) > 0:
        return MDR[list(UMLS_CONCEPT[CUI_ID] >> MDR)[0].name]
    else :
        return False
    
def doc_to_date(path):
    dict_doc_to_date = {}
    with open(path, 'r', newline='') as csvfile :
        csv_reader = csv.DictReader(csvfile, delimiter=";")
        for row in csv_reader:
            doc_id = re.search("=([0-9]{10})", row["LOCATION_CD"]).group(1)
            dict_doc_to_date[doc_id] = re.search("[0-9]{4}-[0-9]{2}-[0-9]{2}",row["START_DATE"]).group(0)
    return dict_doc_to_date

def doc_to_pat(path):
    dict_doc_to_pat = {}
    with open(path, 'r', newline='') as csvfile :
        csv_reader = csv.DictReader(csvfile, delimiter=";")
        for row in csv_reader:
            doc_id = re.search("=([0-9]{10})", row["LOCATION_CD"]).group(1)
            dict_doc_to_pat[doc_id] = row["PATIENT_NUM"]
    return dict_doc_to_pat
## FT 

def returns_norm_num_grade(ann):
    if re.search("([0-5]|III|IV|II|I|V|zéro|un|deux|trois|quatre|cinq)", ann.value):
        num = re.search("([0-5]|III|IV|II|I|V|zéro|un|deux|trois|quatre|cinq)", ann.value).group(0)
        ann.attributes["num"] = num
        if str.lower(num) in ["0", "zéro"] :
            normalized_num = "0"
        elif num in ["1", "I", "un"]:
            normalized_num = "1"
        elif num in ["2", "II","deux"]:
            normalized_num = "2"
        elif num in ["3", "III", "trois"]:
            normalized_num = "3"
        elif num in ["4", "IV", "quatre"]:
            normalized_num = "4"
        elif num in ["5", "V", "cinq"]:
            normalized_num = "5"
        else :
            normalized_num = "null"
    else :
        num = "null"
        normalized_num = "null"
    return num, normalized_num
    
    
def select_stanza_ann_with_span(list_spans, tox_span) :
    selected_spans = []
    in_the_tox_expression = False # pour les tox de plusieurs mots
    for span in list_spans :
        if span[0] == tox_span[0]:
            selected_spans.append(span)
            if span[1] == tox_span[1]: # 1 seul mot dans la tox
                break
            else :
                in_the_tox_expression = True
        elif span[1] < tox_span[1] and in_the_tox_expression:
            selected_spans.append(span)
        elif span[1] == tox_span[1] and in_the_tox_expression:
            selected_spans.append(span)
            break
    return selected_spans


def mine_relations_recursivly(ID_of_ann, document, relations_list) :
    if  len(document.get_relations(head_id = ID_of_ann)) == 0 :
        return(relations_list)
    else :
        thisRelations = [rel for rel in document.get_relations(head_id = ID_of_ann)]
        for rel in thisRelations :
            relations_list.append(rel)
            ID_of_ann = rel.target
            mine_relations_recursivly(ID_of_ann, document, relations_list)
            
            
def creats_dict_span0(doc,ann_type = "regex_grade") :
    dict_span = {}
    list_int_ann = doc.get_annotations(_type = ann_type)
    for ann in list_int_ann :
        dict_span[ann.span[0]] = ann.ID
    return dict_span


def returns_tox_ann(doc, dict_span0, rel_list):
    ann_ID = False
    for rel in rel_list :
        ann_span0 = doc.get_annotation_by_id(rel.head).span[0]
        if ann_span0 in dict_span0 :
            ann_ID =  dict_span0[ann_span0]
            break
    return ann_ID


def rel_ents_of_int(doc):
    list_span_annQ = []
    quickumls_anns = doc.get_annotations(_type="QuickUMLS")
    for annQ in quickumls_anns:
        list_span_annQ.append(annQ.span)
    stanza_annots = doc.get_annotations(_type="Stanza_tox")
    dict_spans={}
    for annS in stanza_annots :
        dict_spans[annS.span] = annS.ID
    list_of_lists_span_co_SQ = []
    for Qspan in list_span_annQ :
        list_of_lists_span_co_SQ.append(select_stanza_ann_with_span(list_spans=[key for key in dict_spans], tox_span=Qspan))
    list_of_relations_list =[]
    for list_span in list_of_lists_span_co_SQ :
        for spanSQ in list_span :
            relations_list = []
            mine_relations_recursivly(ID_of_ann=dict_spans[spanSQ],document=doc, relations_list = relations_list)
            list_of_relations_list.append(relations_list)
    return list_of_relations_list

            
def add_pymedext_relations(doc, rel_list, dict_quickumls_span0, dict_grade_span0):
    list_of_pym_rels = []
    quickumls_ann_ID = returns_tox_ann(doc, dict_quickumls_span0, rel_list) # to onto
    if quickumls_ann_ID :
        #quickumls_ann = doc.get_annotation_by_id(quickumls_ann_ID)
        for rel in rel_list :
            target_ann_span0 = doc.get_annotation_by_id(rel.target).to_dict()["span"][0] 
            if target_ann_span0 in dict_grade_span0 :
                grade_ann_ID = dict_grade_span0[target_ann_span0]
                ## On transforme le type des annotations en to_onto 
                attributes = {"objProp" : "hasGrade"}
                rel = Relation(head = quickumls_ann_ID,
                           target = grade_ann_ID,
                           type = "to_onto",
                           attributes = attributes,
                           source = 'Stanza_tox',
                           source_ID = rel.ID
                          )
                list_of_pym_rels.append(rel)
    return list_of_pym_rels
                         

## tables
def gives_LOCATION_CD(small_location_cd):
    small_location_cd = small_location_cd.replace(".html","")
    while len(small_location_cd) < 10 :
        small_location_cd = "0" + small_location_cd
    return small_location_cd

def returns_Documents_list(list_ann_dict) :
    list_Documents = []
    for ann in list_ann_dict :
        list_Documents.append(Document.from_dict(ann))
    return list_Documents

def keeps_tox_tables(list_Doc) :
    for doc in list_Doc :
        int_anns = doc.get_annotations(_type="toxtable_detect")
        for ann in int_anns :
            if ann.value == "ADE" :
                break
    return ann.value
        
def QuickUML_to_list_of_doc(df_line, matcher) :
    list_of_docs = df_line["annotated_Documents"]
    for doc in list_of_docs :
        int_anns = doc.get_annotations(_type="table_line")
        for ann in int_anns :
            if not ann.attributes['first_line'] :
                quickumls = matcher.match(ann.attributes['term'], best_match=True, ignore_syntax=False)
                ann.attributes["QuickUMLS"] = quickumls
                
def returns_norm_num_grade2(str_grade):
    if re.search("([0-5]|III|IV|II|I|V)", str_grade):
            num = re.search("([0-5]|III|IV|II|I|V)", str_grade).group(0)
            if num == "0" :
                num_grade= "0"
            elif num in ["1", "I"]:
                num_grade = "1"
            elif num in ["2", "II"]:
                num_grade = "2"
            elif num in ["3", "III"]:
                num_grade = "3"
            elif num in ["4", "IV"]:
                num_grade = "4"
            elif num in ["5", "V"]:
                num_grade = "5"
            else :
                num_grade = "null"
    else :
        num = "null"
        num_grade = "null"
        
    return num, num_grade
                
def table_df_to_onto(df_line, onto, dict_class_grade, index, processClass, dict_doc_to_pat, dict_doc_to_date):
    with onto :
        list_of_docs = df_line["annotated_Documents"]
        num_table = df_line["NUM_TABLE"]
        for doc in list_of_docs :
            # doc_id
            id_doc_value = doc.source_ID
            # provenance
            docClass_name = "DOC_" + id_doc_value
            if docClass_name not in [c.name for c in onto.classes()] :
                parent = PROVO["Entity"]
                docClass = types.new_class(docClass_name, (parent,))
            else:
                docClass = getattr(onto, docClass_name)
            table_ind_name = "table_"+ id_doc_value + "_" +str(num_table)
            table_ind = onto.Tables(table_ind_name)
            PROVO.wasDerivedFrom[table_ind].append(docClass)
            # patient
            pat_value = dict_doc_to_pat[id_doc_value]
            if pat_value not in [ind.name for ind in onto.Patient.instances()]:
                name_ind_pat = pat_value
                name_ind_pat = onto.Patient(pat_value)
            else :
                name_ind_pat = getattr(onto, pat_value)
            # date
            date_value = dict_doc_to_date[id_doc_value]
            if date_value not in [ind.name for ind in onto.StartDate.instances()]:
                name_ind_date = date_value
                name_ind_date = onto.AbsoluteStartDate(name_ind_date)
            else :
                name_ind_date = getattr(onto, date_value)
            # annotations
            int_anns = doc.get_annotations(_type="table_line")
            meddra = False
            for ann in int_anns :
                if not ann.attributes['first_line'] :
                    tox_value = ann.attributes["term"]
                    # cui
                    cui = False
                    # Lié au traitement
                    liett = None
                    # Date
                    start_date_in_table_value = None
                    end_date_in_table_value = None
                    if "QuickUMLS" in ann.attributes :
                        if ann.attributes["QuickUMLS"] :
                            cui = True
                            cui_code = ann.attributes["QuickUMLS"][0][0]["cui"]
                            cui_class = UMLS_CONCEPT[cui_code]
                    #meddra
                    if owl_transcode_cui_to_meddra(cui_code) :
                        meddra_class = owl_transcode_cui_to_meddra(cui_code)
                        meddra = True
                    # grade
                    for key in ann.attributes :
                        if re.search("grade", key, re.IGNORECASE) :
                            att_grade = key
                    grade_value = ann.attributes[att_grade]
                    num, num_grade = returns_norm_num_grade2(grade_value)
                    # Lié au TT
                    if "Lié    au TT (oui/non)" in ann.attributes :
                        if re.search("(oui|non)", ann.attributes["Lié    au TT (oui/non)"], re.IGNORECASE) :
                            ans = re.search("(oui|non)", ann.attributes["Lié    au TT (oui/non)"], re.IGNORECASE).groupe(0)
                            if str.lower(ans) == "oui" :
                                liett = True
                            else :
                                liett = False
                        else :
                            liett = None
                    if "Date    début" in ann.attributes :
                        start_date_in_table_value = ann.attributes["Date    début"]
                    if "Date    fin" in ann.attributes :
                        end_date_in_table_value = ann.attributes["Date    fin"]
                    # instanciations
                    ClassGrade = onto[dict_class_grade[num_grade]]
                    name_ind_grade = "table"+ "_" + str(index) + "_" + grade_value
                    name_ind_grade = name_ind_grade.replace(" ","_")
                    name_ind_grade = ClassGrade(name_ind_grade,
                               hasValueInTable = grade_value)
                    name_ind_grade.label.append(grade_value)
                    # date
                    name_ind_date_deb = "table"+ "_" + str(index) + "_" + start_date_in_table_value
                    name_ind_date_fin = "table"+ "_" + str(index) + "_" + end_date_in_table_value
                    name_ind_date_deb = onto.AbsoluteStartDate(name_ind_date_deb,
                                         hasValueInTable = start_date_in_table_value)
                    name_ind_date_fin = onto.AbsoluteStartDate(name_ind_date_fin,
                                         hasValueInTable = end_date_in_table_value )
                    name_ind_date_deb.label.append(start_date_in_table_value)
                    name_ind_date_fin.label.append(end_date_in_table_value)
                    # toxicité
                    name_ind_tox = "table"+ "_" + str(index) + "_" + tox_value
                    name_ind_tox = name_ind_tox.replace(" ", "_")
                    name_ind_tox = onto.ChemotherapyToxicity(name_ind_tox,
                                                        hasValueInQST = tox_value,
                                                        hasGrade = name_ind_grade,
                                                        hasAbsoluteStartDate = [name_ind_date],
                                                        isRelatedToPatient = name_ind_pat
                                                       )
                    if cui :
                        name_ind_tox.is_a.append(cui_class)
                    if meddra :
                        name_ind_tox.is_a.append(cui_class)
                    name_ind_tox.label.append(tox_value)
                    # provenance
                    name_ind_tox.is_a.append(PROVO['Entity'])
                    ind_generation = PROVO.Generation()
                    PROVO.qualifiedGeneration[name_ind_tox].append(ind_generation)
                    PROVO.influencer[ind_generation].append(table_ind)
                    PROVO.activity[ind_generation].append(processClass)
                    PROVO.used[processClass].append(table_ind)

## QST

def qst_grade_df_to_onto(df_line, onto, dict_class_grade, index, processClass ):
    with onto :
        meddra=False
        # toxicité
        tox_value = df_line.NAME_CHAR
        qst_type = df_line.TYPE
        qst_concept = str(df_line.CONCEPT_CD).replace("|","_")
        cui_code = df_line.QuickUMLS[0][0]["cui"]
        cui_class = UMLS_CONCEPT[cui_code]
        # provenance
        QSTClass_name = "QST_" + qst_concept
        if QSTClass_name not in [c.name for c in onto.classes()] :
            parent = PROVO["Entity"]
            QSTClass= types.new_class(QSTClass_name, (parent,))
        else:
            QSTClass = getattr(onto, QSTClass_name)
        QSTtype_class_name = "QST_" + qst_type
        if QSTtype_class_name not in [c.name for c in onto.classes()] :
            parent = PROVO["Entity"]
            QSTtype_class= types.new_class(QSTtype_class_name, (parent,))
        else:
            QSTtype_class = getattr(onto, QSTtype_class_name)
        qst_ind_name = "QST_"+ qst_concept + "_" + str(index)
        qst_ind = onto.QST_answer(qst_ind_name)
        PROVO.wasDerivedFrom[qst_ind].append(QSTClass)
        PROVO.wasDerivedFrom[QSTClass].append(QSTtype_class)
        # Meddra
        if owl_transcode_cui_to_meddra(cui_code) :
            meddra_class = owl_transcode_cui_to_meddra(cui_code)
            meddra = True
        # grade
        grade_value = df_line.TVAL_CHAR
        # patient
        pat_value = str(df_line.PATIENT_NUM)
        # date 
        date_value = re.search("[0-9]{4}-[0-9]{2}-[0-9]{2}",df_line.START_DATE).group(0)
        # instanciations
        # grade
        ClassGrade = onto[dict_class_grade[df_line.GRADE_NUM]]
        name_ind_grade = str(index) + "_" + str(df_line.CONCEPT_CD).replace("|","") + "_" + grade_value
        name_ind_grade = name_ind_grade.replace(" ","_")
        name_ind_grade = name_ind_grade.replace(":","")
        name_ind_grade = ClassGrade(name_ind_grade,
                               hasValueInQST = grade_value)
        name_ind_grade.label.append(grade_value)
        # date
        if date_value not in [ind.name for ind in onto.StartDate.instances()]:
            name_ind_date = date_value
            name_ind_date = onto.AbsoluteStartDate(name_ind_date)
        else :
            name_ind_date = getattr(onto, date_value)
        # patient
        if pat_value not in [ind.name for ind in onto.Patient.instances()]: 
            name_ind_pat = pat_value
            name_ind_pat = onto.Patient(pat_value)
        else :
            name_ind_pat = getattr(onto, pat_value) 
        # toxicité
        name_ind_tox = str(index) + "_" + str(df_line.CONCEPT_CD).replace("|","") + "_" + tox_value
        name_ind_tox = name_ind_tox.replace(":","")
        name_ind_tox = name_ind_tox.replace(" ","_")
        name_ind_tox = onto.ChemotherapyToxicity(name_ind_tox,
                                            hasValueInQST = tox_value,
                                            hasGrade = name_ind_grade,
                                            hasAbsoluteStartDate = [name_ind_date],
                                            isRelatedToPatient = name_ind_pat,
                                            comesFrom = qst_type
                                           )
        name_ind_tox.is_a.append(cui_class)
        if meddra :
            name_ind_tox.is_a.append(meddra_class)
        name_ind_tox.label.append(tox_value)
        # provenance
        name_ind_tox.is_a.append(PROVO['Entity'])
        ind_generation = PROVO.Generation()
        PROVO.qualifiedGeneration[name_ind_tox].append(ind_generation)
        PROVO.influencer[ind_generation].append(qst_ind)
        PROVO.activity[ind_generation].append(processClass)
        PROVO.used[processClass].append(qst_ind)
    