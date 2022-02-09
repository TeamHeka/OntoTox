from pymedextcore.annotators import Annotation, Annotator, Relation
from pymedextcore.document import Document
import glob
import re
import json
from flashtext import KeywordProcessor
import pandas as pd

try:
    from quickumls import QuickUMLS
    from quickumls.constants import ACCEPTED_SEMTYPES
except:
    print('QuickUMLS not installed. Please use "pip install quickumls"')
    
try:
    import stanza
except:
    print('Stanza not installed. Please use "pip install stanza",(go on https://stanfordnlp.github.io/stanza/index.html)jyhnvb"')


from constants import SECTION_DICT
from constantsTox import FIRST_CELL_DICT
from verbs import verbs_list


import cudf

class TableLineRemover(Annotator) :
    
    def annotate_function(self, _input):
        inp= self.get_first_key_input(_input)[0]
        txt = self.rm_lines_with_pipes(inp.value)

        return([Annotation(
            type = self.key_output,
            value = txt,
            span = (0, len(txt)),
            source = self.ID,
            source_ID = inp.ID
        )])
    
    @staticmethod
    def rm_lines_with_pipes(raw_text):
        line_list=[]
        for line in raw_text.split('\n'):
            if re.search("\|.*\|", line):
                line_list.append("\n")
            else :
                line_list.append(line)
        txt=""
        for line in line_list :
            txt = txt + line
        return txt

    
class TableLineExtractor(Annotator) :
    
    def annotate_function(self, _input):
        inp= self.get_first_key_input(_input)[0]
        table = self.split_lines(inp.value)
        
        res=[]
        offset = 0
        start = 0
        end = 0
        
        for line in table :
            
            start = inp.value.find(line) + offset
            end = start + len(line)
            
            res.append(Annotation(
                type = self.key_output,
                value = line,
                span = (start,end),
                source = self.ID,
                source_ID = inp.ID,
                attributes = {}
            ))
            
            offset = end
            
        return(res)
    
    @staticmethod    
    def split_lines(table):
        return(re.split("<tr>|</tr>",table)[1:-1])
    

    
class ToxTableDetector(Annotator):
    
    def __init__(self, key_input, key_output, ID, first_cell_dict = FIRST_CELL_DICT):
        
        self.first_cell_dict=first_cell_dict
        super().__init__(key_input, key_output, ID)
            
    def annotate_function(self, _input):
        inp= self.get_first_key_input(_input)[0]
        #print("!!!!!!!!!!!!!! ",inp.value, "\n\n")
        try :
            df = self.df_from_table(inp.value)
            first_cell = self.first_cell_reader(df)
            FLAG = self.is_it_a_tox_cell(first_cell, self.first_cell_dict)
        except ValueError :
            FLAG = False
        return([Annotation(
            type = self.key_output,
            value = FLAG,
            span = (0, len(inp.value)),
            source = self.ID,
            source_ID = inp.ID,
            attributes = {'table':inp.value}
        )])
    
    @staticmethod 
    def df_from_table(table):
        return(pd.read_html(table)[0])
    
    @staticmethod 
    def first_cell_reader(df):
        return(df.at[0,0])
    
    @staticmethod 
    def is_it_a_tox_cell(cell, first_cell_dict):
        FLAG = False
        for table_type in first_cell_dict :
            for pattern in first_cell_dict[table_type]:
                pattern = str(pattern)
                cell = str(cell)
                if re.search(pattern, cell, re.IGNORECASE) :
                    FLAG = table_type
                    break
        return(FLAG)
    
    
    
class ToxTableDetector(Annotator):
    
    def __init__(self, key_input, key_output, ID, first_cell_dict = FIRST_CELL_DICT):
        
        self.first_cell_dict=first_cell_dict
        super().__init__(key_input, key_output, ID)
            
    def annotate_function(self, _input):
        inp= self.get_first_key_input(_input)[0]
        #print("!!!!!!!!!!!!!! ",inp.value, "\n\n")
        try :
            df = self.df_from_table(inp.value)
            first_cell = self.first_cell_reader(df)
            FLAG = self.is_it_a_tox_cell(first_cell, self.first_cell_dict)
        except ValueError :
            FLAG = False
        return([Annotation(
            type = self.key_output,
            value = FLAG,
            span = (0, len(inp.value)),
            source = self.ID,
            source_ID = inp.ID,
            attributes = {'table':inp.value}
        )])
    
    @staticmethod 
    def df_from_table(table):
        return(pd.read_html(table)[0])
    
    @staticmethod 
    def first_cell_reader(df):
        return(df.at[0,0])
    
    @staticmethod 
    def is_it_a_tox_cell(cell, first_cell_dict):
        FLAG = False
        for table_type in first_cell_dict :
            for pattern in first_cell_dict[table_type]:
                pattern = str(pattern)
                cell = str(cell)
                if re.search(pattern, cell, re.IGNORECASE) :
                    FLAG = table_type
                    break
        return(FLAG)
    
    
    
    
class ToxTableLineExtractor(Annotator) :
    
    def annotate_function(self, _input):
        inp= self.get_first_key_input(_input)[0]
       
        start = 0
        end = 0
        
        if inp.value != False :
            res = []
            table = self.split_lines(inp.attributes['table'])
            
            first_line = table[0]
            end = start + len(first_line)
            first_line = self.clean_line(table[0])
            cells_list = self.split_cells(first_line)
            list_of_attributes = cells_list[1:]
            
            
            res.append(Annotation(
                    type = self.key_output,
                    value = first_line,
                    span = (start,end),
                    source = self.ID,
                    source_ID = inp.ID,
                    attributes = {'first_line':True, 'type_table':inp.value, 'list_of_attributes': list_of_attributes}
                ))

            for line in table[1:] :

                start = end + 1
                end = start + len(line)
                
                line = self.clean_line(line)
                cells_list = self.split_cells(line)
                result_attributes = cells_list[1:]
                term = cells_list[0]
                
                
                attributes={}
                attributes['term'] = term
                attributes['first_line'] = False
                attributes['type_table'] = 'ADE'
                for couple in zip(list_of_attributes, cells_list[1:]):
                    attributes[couple[0]] = couple[1]
                                
                res.append(Annotation(
                    type = self.key_output,
                    value = term,
                    span = (start,end),
                    source = self.ID,
                    source_ID = inp.ID,
                    attributes = attributes
                    ))
                    

        else :
            res = [Annotation(
                    type = self.key_output,
                    value = "not_tox_table",
                    span = (start,end),
                    source = self.ID,
                    source_ID = inp.ID,
                    attributes = {}
                )]
            
        return(res)
    
    
    @staticmethod    
    def split_lines(table):
        lines_list= re.split("</tr><tr>", table)
        lines_list[0]=lines_list[0].split("<tr>")[1]
        lines_list[-1] = lines_list[-1].split("</tr>")[0]
        return(lines_list)
    
    
    @staticmethod    
    def clean_line(line):
        list_diamonds=re.findall('(<.*?>)', line)
        set_diamonds = set(list_diamonds)
        set_diamonds_to_remove = set_diamonds.difference({'<td>','</td>'})
        for el in set_diamonds_to_remove :
            line = line.replace(el,"")
        return(line)
    
    @staticmethod    
    def split_cells(line):
        cells_list= re.split("</td><td>", line)
        cells_list[0]=cells_list[0].split("<td>")[1]
        cells_list[-1] = cells_list[-1].split("</td>")[0]
        return(cells_list)
    
    


class QuickUMLSAnnotator(Annotator):

    def __init__(self, key_input, key_output, ID,
                quickumls_fp = '/Users/antoine/git/QuickUMLS/umls_data/',
                overlapping_criteria = "length", # "score" or "length"
                threshold = 0.9,
                similarity_name = "jaccard", # Choose between "dice", "jaccard", "cosine", or "overlap".
                window = 5,
                accepted_semtypes = ACCEPTED_SEMTYPES):

        super().__init__(key_input, key_output, ID)


        self.matcher = QuickUMLS(quickumls_fp=quickumls_fp ,
                                 overlapping_criteria=overlapping_criteria,
                                 threshold=threshold,
                                 window=window,
                                 similarity_name=similarity_name,
                                accepted_semtypes=accepted_semtypes)


    def match(self, text):
        return self.matcher.match(text)

    def annotate_function(self, _input):

        inp = self.get_all_key_input(_input)
        
        res = []
        #print("inp quickumls", inp)
        #print("len(inp) quickumls", len(inp))
        

        for sent in inp:
            
            #print("sent.value quickumls",sent.value)

            ents = self.match(sent.value)

            if sent.attributes is None:
                sent.attributes = {}

            for ent in ents:
                
                #print("sent.value", sent.value)

                ent_attr = {'cui':ent[0]['cui'],
                           'label': ent[0]['term'],
                           'semtypes': list(ent[0]['semtypes']),
                           'score': ent[0]['similarity'],
                            'snippet': sent.value,
                            'snippet_span' : sent.span
                           }

                start = sent.span[0] + ent[0]['start']
                end = sent.span[0] + ent[0]['end']

                res.append(Annotation(
                    type = self.key_output,
                    value = ent[0]['ngram'],
                    span = (start, end),
                    source = self.ID,
                    source_ID = sent.ID,
                    attributes = {**sent.attributes.copy() , **ent_attr}
                ))

        return res
    
    
# class SentWithToxSelector(Annotator) :
    
#     def annotate_function(self, _input):

#         inp = self.get_all_key_input(_input)
        
#         for el in inp:
#             sent_id = el.source_ID
            
class StanzaAnnotator(Annotator):
    
    def __init__(self, key_input, key_output, ID,
                lang = 'fr',
                #dir=DEFAULT_MODEL_DIR,
                #package='default',
                processors = 'tokenize,mwt,pos,lemma,depparse', # stanza processors
                #logging_level=None,
                #verbose=None, 
                #use_gpu=True,
                #**kwargs
                ):

        super().__init__(key_input, key_output, ID)


        self.nlp = stanza.Pipeline(lang = lang, processors = processors)
        
        

        
    def annotate_function(self, _input):

        inp = self.get_all_key_input(_input)
        
        #print("inp", inp)
        
        res = []
        #ann_list = []
        #rel_list = []
        
        for el in inp:
            stanza_doc = self.nlp(el.value)
            #if word.text == inp.value : # si le mot correspond bien à la tox
            #sent_counter = 0
            for sent in stanza_doc.sentences :
                #sent_counter += 1
                dict_word_ID_to_ann_ID = {}
                list_id_par_rel=[]
                #dict_ann_ID_to_complete_annotation = {}
                for word in sent.words :
                    attributes = word.to_dict()
                    if 'misc' in attributes :
                        span0,span1 = int(el.span[0]) + int(attributes['misc'].split('|')[0].split("=")[-1]), int(el.span[0]) + int(attributes['misc'].split('|')[1].split("=")[-1])
                        ann = Annotation(
                            type = self.key_output,
                            value = word.text,
                            span = (span0, span1),
                            source = self.ID,
                            source_ID = el.ID,
                            attributes = attributes
                            )
                        dict_word_ID_to_ann_ID[word.id] = ann.ID
                        res.append(ann)
                    else : # on est sur un mot du type "du" = "de"+"le"
                        if word.parent.id not in dict_word_ID_to_ann_ID :
                            word_parent = word.parent
                            attributes_parent = word_parent.to_dict()[0]
                            attributes_child1 = word_parent.to_dict()[1]
                            attributes_child2 = word_parent.to_dict()[2]
                            attributes_child = {"child_1" : attributes_child1 , "child_2" : attributes_child2}
                            upos_value = attributes_child1['upos'] + "_" + attributes_child2['upos']
                            lemma_value = attributes_child1['lemma'] + "_" + attributes_child2['lemma']
                            all_att = {"upos" : upos_value, "lemma": lemma_value, **attributes_parent, **attributes_child}
                            span0,span1 = int(el.span[0]) + int(attributes_parent['misc'].split('|')[0].split("=")[-1]), int(el.span[0]) + int(attributes_parent['misc'].split('|')[1].split("=")[-1])
                            ann = Annotation(
                                type = self.key_output,
                                value = word_parent.text,
                                span = (span0, span1),
                                source = self.ID,
                                source_ID = el.ID,
                                attributes = all_att
                                )
                            dict_word_ID_to_ann_ID[word.parent.id] = ann.ID
                            # au cas où du serait la head de qq "du fait"
                            dict_word_ID_to_ann_ID[word.id] = ann.ID 
                            dict_word_ID_to_ann_ID[attributes_child2["id"]] = ann.ID
                            res.append(ann)
                        
                    
                    #dict_ann_ID_to_complete_annotation[word.id] = ann
                    #res.append(ann)
                for word in sent.words : 
                    if word.head > 0 : # head != root
                        attributes = word.to_dict()
                        if 'misc' in attributes :
                            deprel_value = word.to_dict()['deprel'].replace(":","_")
                            attributes_rel = {'deprel': deprel_value}
                            try :
                                rel = Relation(
                                    head = dict_word_ID_to_ann_ID[word.head],
                                    target = dict_word_ID_to_ann_ID[word.id],
                                    type = self.key_output,
                                    source = self.ID,
                                    source_ID = el.ID,
                                    attributes = attributes_rel
                                    )
                                res.append(rel)
                            except KeyError :
                                    print("pb")
                        else :
                            if word.parent.id not in list_id_par_rel :
                                list_id_par_rel.append(word.parent.id)
                                word_parent = word.parent
                                attributes_parent = word_parent.to_dict()[0]
                                attributes_child1 = word_parent.to_dict()[1]
                                attributes_child2 = word_parent.to_dict()[2]
                                attributes_child = {"child_1" : attributes_child1 , "child_2" : attributes_child2}
                                deprel_value = attributes_child1['deprel'].replace(":","_") + "_" + attributes_child2['deprel'].replace(":","_")
                                attributes_rel = {'deprel': deprel_value}
                                try :
                                    rel = Relation(
                                        head = dict_word_ID_to_ann_ID[attributes_child1["head"]],
                                        target = dict_word_ID_to_ann_ID[word.parent.id],
                                        type = self.key_output,
                                        source = self.ID,
                                        source_ID = el.ID,
                                        attributes = attributes_rel
                                        )
                                    res.append(rel)
                                except KeyError :
                                    print("pb")
                                
                                #continue # skip the second word
                              
                        #ann1 = dict_ann_ID_to_complete_annotation[word.head]
                        #ann2 = dict_ann_ID_to_complete_annotation[word.id]
                        #tuple_res = (ann1,ann2,rel)
                        
                    #else : # head is root
                    #    ann = dict_ann_ID_to_complete_annotation[word.id]
                    #    res.append(ann)
        return res

            
            

            
            