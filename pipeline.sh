cd src
printf "Creating OntoTox structure ... \n\n"
python3 creatsOntoTox.py
printf "\n\nInstantiating OntoTox with text ... \n\n"
python3 process_free_text.py
printf "\n\nInstantiating OntoTox with tables ... \n\n"
python3 process_tables.py
printf "\n\nInstantiating OntoTox with qst ... \n\n"
python3 process_qst.py
printf "\n\n Done."