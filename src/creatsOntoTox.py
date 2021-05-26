import sys
from owlready2 import *

def main(argv=None):
    
    try:
        path_owl = argv[argv.index("--pathOut") + 1]
    except ValueError:
        try:
            path_owl = argv[argv.index("-p") + 1]
        except ValueError:
            path_owl = "../owl_files/"
            
    try:
        name_owl = argv[argv.index("--fileName") + 1]
    except ValueError:
        try:
            name_owl = argv[argv.index("-f") + 1]
        except ValueError:
            name_owl = "OntoTox.owl"
            
    onto = get_ontology("http://OntoTox.owl#")

    with onto:

        # 1 Classes definitions
        class ChemotherapyToxicity(Thing): pass

        class Patient(Thing) : pass

        class Grade(Thing): pass
        class Grade0(Grade): pass
        class Grade1(Grade): pass
        class Grade2(Grade): pass
        class Grade3(Grade): pass
        class Grade4(Grade): pass
        class Grade5(Grade): pass
        class GradeNull(Grade): pass


        class Qualifier(Thing): pass

        class StartDate(Thing): pass
        class RelativeStartDate(StartDate): pass
        class AbsoluteStartDate(StartDate): pass

        AllDisjoint([RelativeStartDate, AbsoluteStartDate])

        class Drug(Thing): pass

        AllDisjoint([ChemotherapyToxicity, Qualifier, StartDate, Drug, Patient, Grade])


        # 2 Object Properties definition
        class hasGrade(ChemotherapyToxicity >> Grade, FunctionalProperty): pass
        class associatedWithTreatment(ChemotherapyToxicity >> Drug): pass
        class hasRelativeStartDate(ChemotherapyToxicity >> RelativeStartDate): pass
        class hasAbsoluteStartDate(ChemotherapyToxicity >> AbsoluteStartDate): pass
        class isRelatedToPatient( ChemotherapyToxicity >> Patient, FunctionalProperty): pass
        class isAffectedBy( Patient >> ChemotherapyToxicity) :
            inverse = isRelatedToPatient


        # 3 Data Properties definition
        class isHypothetical(ChemotherapyToxicity >> bool, FunctionalProperty): pass
        class isNegative(ChemotherapyToxicity >> bool, FunctionalProperty): pass
        class concernsPatient(ChemotherapyToxicity >> bool, FunctionalProperty): pass
        class hasValueInText(ChemotherapyToxicity >> str, FunctionalProperty): pass
        class hasValueInQST(ChemotherapyToxicity >> str, FunctionalProperty): pass
        class hasValueInTable(ChemotherapyToxicity >> str, FunctionalProperty): pass
        class comesFrom(ChemotherapyToxicity >> str, FunctionalProperty): pass


    onto.save(path_owl + name_owl)
    
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))