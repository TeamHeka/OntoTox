import re, os, time, csv, sys, yaml
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
from annotatorsTox import QuickUMLSAnnotator, StanzaAnnotator, TableLineRemover


def main(argv=None):
    
    try:
        data_FT = argv[argv.index("--data") + 1]
    except ValueError:
        try:
            data_FT = argv[argv.index("-d") + 1]
        except ValueError:
            data_FT = cfg["data"]["NR"]
    
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
            name_owl_in = "OntoTox.owl"
                        
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

    
    # Load free text data
    file_list=os.listdir(data_FT)
    docs=[]
    for file in file_list :
        docs.append(rawtext_loader(data_FT + file))
    
    # 1/ Annotations
    ## pymedext annotators
    tableremover = TableLineRemover(['raw_text'], 'table_remover', 'tableRemover:v1')
    endlines = Endlines(['table_remover'], 'endlines', 'endlines:v1')
    sentences = SentenceTokenizer(['endlines'], 'sentence', 'sentenceTokenizer:v1')
    hypothesis = Hypothesis(['sentence'], 'hypothesis', 'hypothesis:v1')
    family = ATCDFamille(['sentence'], 'context', 'ATCDfamily:v1')
    syntagmes = SyntagmeTokenizer(['sentence'], 'syntagme', 'SyntagmeTokenizer:v1')
    negation = Negation(['syntagme', 'sentence'], 'negation', 'Negation:v1')
    quickumls = QuickUMLSAnnotator(['sentence'],'QuickUMLS', 'QuickUMLS:v1',quickumls_fp=quickumls_fp)
    regex_grade = RegexMatcher(['endlines', 'syntagme'], 'regex_grade', 'RegexMatcher:v1', regex_grade_file)
    pipeline1 = Pipeline(pipeline = [tableremover, endlines, sentences, hypothesis, family, syntagmes, negation, quickumls, regex_grade])
    annotated_docs = pipeline1.annotate(docs)
    annotated_pymedext_documents = [Document.from_dict(annotated_doc) for annotated_doc in annotated_docs]
    ## grade normalization 
    for thisDoc in annotated_pymedext_documents :
        anns=thisDoc.get_annotations(_type="regex_grade")
        for ann in anns :
            num, normalized_num = returns_norm_num_grade(ann)
            ann.attributes["num"] = num
            ann.attributes["normalized_num"] = normalized_num
    ## Select sentences with at least one toxicity entity  
    for thisDoc in annotated_pymedext_documents :
        list_id_sent_tox = []
        for annQ in thisDoc.get_annotations(_type="QuickUMLS"):
            if annQ.source_ID not in list_id_sent_tox :
                list_id_sent_tox.append(annQ.source_ID)
    set_sent_tox = []        
    for id_sent_tox in list_id_sent_tox :
        annots = thisDoc.get_annotation_by_id(id_sent_tox)
        annots.type = "sentence_tox"
    
    # 2/ Relations
    stanzaparser_tox = StanzaAnnotator(['sentence_tox'], 'Stanza_tox', 'Stanza:v1')
    pipeline2 = Pipeline(pipeline = [stanzaparser_tox])
    annotated_docs2 = pipeline2.annotate(annotated_pymedext_documents)
    annotated_pymedext_documents2 = [Document.from_dict(annotated_doc) for annotated_doc in annotated_docs2]
    ## Adding relations between entities of interest
    for doc in annotated_pymedext_documents2:
        list_of_relations_list = rel_ents_of_int(doc)
        ## to onto 
        dict_quickumls_span0 = creats_dict_span0(doc, ann_type = "QuickUMLS") # to onto
        dict_grade_span0 = creats_dict_span0(doc, ann_type = "regex_grade") # to onto pour le grade
        for rel_list in list_of_relations_list :
            if rel_list :
                list_of_pym_rels = add_pymedext_relations(doc, rel_list, dict_quickumls_span0, dict_grade_span0)
                for rel in list_of_pym_rels :
                    doc.relations.append(rel)
                        
    # 3/ Instantiates OntoTox
    dict_doc_to_date = doc_to_date(path = cfg["data"]["reports_metadata"])
    dict_doc_to_pat = doc_to_pat(path = cfg["data"]["reports_metadata"])
    onto = get_ontology(path_owl + name_owl_in).load()
    with onto :
        class FreeText(PROVO.Entity): pass
        class ProcessFreeText(PROVO.Agent): pass
        timestr = time.strftime("%Y%m%d-%H%M%S")
        name_process = "process_free_text" + timestr
        processClass = types.new_class(name_process, (PROVO.Activity,))
        PROVO.wasAssociatedWith[processClass].append(ProcessFreeText)
        for doc in annotated_pymedext_documents2:
            # doc_id
            id_doc_value = doc.source_ID 
            # provenance
            docClass_name = "DOC_" + id_doc_value
            if docClass_name not in [c.name for c in onto.classes()] :
                parent = PROVO["Entity"]
                docClass = types.new_class(docClass_name, (parent,))
            else:
                docClass = getattr(onto, docClass_name)
            free_text_ind_name = "FT_"+ id_doc_value
            free_text_ind = FreeText(free_text_ind_name)
            PROVO.wasDerivedFrom[free_text_ind].append(docClass)
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
            anns_tox_quickumls = doc.get_annotations(_type="QuickUMLS")       
            for ann_tox in anns_tox_quickumls :
                meddra = False
                # classe concept UMLS
                cui_code = ann_tox.attributes["cui"]
                cui_label = ann_tox.attributes["label"]
                if UMLS_CONCEPT[cui_code] is not None :
                    cui = True
                    cui_class = UMLS_CONCEPT[cui_code]
                    if owl_transcode_cui_to_meddra(cui_code) :
                        meddra_class = owl_transcode_cui_to_meddra(cui_code)
                        meddra = True
                else :
                    print("no with", cui_code)
                    cui = False
                tox_hyp = ann_tox.attributes["hypothesis"] == "hypothesis"
                tox_neg = ann_tox.attributes["negation"] == "neg"
                tox_pat = ann_tox.attributes["context"] == "patient"
                tox_value = ann_tox.value
                name_ind_tox = ann_tox.ID
                name_ind_tox = onto.ChemotherapyToxicity(name_ind_tox,
                                                       isHypothetical = tox_hyp,
                                                       isNegative = tox_neg,
                                                       concernsPatient = tox_pat,
                                                       hasValueInText = tox_value,
                                                       hasAbsoluteStartDate = [name_ind_date],
                                                       isRelatedToPatient = name_ind_pat)

                if cui :
                    name_ind_tox.is_a.append(cui_class)
                    if meddra :
                        name_ind_tox.is_a.append(meddra_class)
                name_ind_tox.label.append(tox_value)
                name_ind_pat.isAffectedBy.append(name_ind_tox)
                # provenance
                name_ind_tox.is_a.append(PROVO['Entity'])
                ind_generation = PROVO.Generation()
                PROVO.qualifiedGeneration[name_ind_tox].append(ind_generation)
                PROVO.influencer[ind_generation].append(free_text_ind)
                PROVO.activity[ind_generation].append(processClass)
                PROVO.used[processClass].append(free_text_ind)
                
        # relations
        for doc in annotated_pymedext_documents2:
            id_doc_value = doc.source_ID
            relations_tox = doc.get_relations(_type="to_onto")
            for rel in relations_tox :
                if rel.attributes["objProp"] == "hasGrade":
                    # créer les individus grades
                    ann_grade = doc.get_annotation_by_id(rel.target)
                    ClassGrade = onto[dict_class_grade[ann_grade.attributes["normalized_num"]]]
                    grade_hyp = ann_grade.attributes["hypothesis"] == "hypothesis"
                    grade_neg = ann_grade.attributes["negation"] == "neg"
                    grade_pat = ann_grade.attributes["context"] == "patient"
                    grade_value = ann_grade.value
                    name_ind_grade = ann_grade.ID
                    name_ind_grade = ClassGrade(name_ind_grade,
                                              isHypothetical = grade_hyp,
                                              isNegative = grade_neg,
                                              concernsPatient = grade_pat,
                                              hasValueInText = grade_value)
                    ann_tox_ID = doc.get_annotation_by_id(rel.head).to_dict()["ID"]
                    name_ind_tox = getattr(onto, ann_tox_ID)
                    name_ind_grade.label.append(grade_value)
                    try :
                        onto.hasGrade[name_ind_tox].append(name_ind_grade)
                    except AttributeError :
                        print("ann_tox_ID", ann_tox_ID)
                    
    name_owl = name_owl_in.replace(".owl", "") + "_FT.owl"    
    onto.save(path_owl + name_owl)
    
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))