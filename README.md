# auto-abbreviation

This script automatically converts journal names to abbreviations in `.bib` files. It leverages excerpts from the `bibtexparser` package to parse `.bib` files and applies rules from a journal abbreviations list to perform the conversions.

## Usage

### Overleaf
On Overleaf, this script can be imported using the following command:

```
\input{|python abbr.py bibfile-1.bib bibfile-2.bib bibfile-3.bib}
```
in the preamble of your document. This command will execute the script and generate a consolidated `.bib` file named `abbreviated.bib` in the project directory. You can then use this file in the `\bibliography{abbreviated.bib}` command to include the references in your document.


### Local Environment
To use this script locally, simply run 
```
python abbr.py bibfile-1.bib bibfile-2.bib bibfile-3.bib
```
This will generate a consolidated `.bib` file named `abbreviated.bib`, which contains all references with their respective abbreviations. You can then use this file in the `\bibliography{abbreviated.bib}` command to include the references in your document.


## Notes

- Overleaf stores newly generated files in its cache rather than the user's project folder. These cached files are used during compilation and do not interfere with the original project files. Thus, the consolidated `.bib` file will not be visible in the project folder but will be available for use in the document.

## To Do
- Add a command-line argument to allow users to specify the name of the output `.bib` file.
- Refactor the script to remove unused portions of the `bibtexparser` code, ensuring only relevant functionality is retained.

## Acknowledgements
This script shamelessly borrows code from the `bibtexparser` package, which is licensed under the MIT License. The original code can be found [here](https://github.com/sciunto-org/python-bibtexparser).