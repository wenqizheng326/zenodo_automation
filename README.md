# zenodo_automation

## How to set up for use
1. Clone this repository via ssh
```
git@github.com:wenqizheng326/zenodo_automation.git
```
2. Go to directory of the repository
   - check that you are in the directory by using the command
     ```
     ls
     ```
     This should show you the files in your current directory
   - You are in the correct directory if you see the file called zenodo.py
     
3. Create an .env file
   -  This is where you add your zenodo api token so you have access to more databases on Zenodo
   -  Use .env.example for what the file should look like
  
## Usage
- To search:
  - Use the command
     ```python zenodo.py search <keywords you want to search by>```
    -  Ex:
```
python zenodo.py search climate
```
   
  - You can search via multiple keywords
    -  Ex:
```
python zenodo.py search "machine learning" biology
```
   
- To download:
  -  You need the database id
      -  This can be found in the URL endpoint
          -  Ex: if the URL is https://zenodo.org/record/13960343, then the id is 13960343
              -  The URL is produced when using search command
  -  Use the command
  ```python zenodo.py download <database id> <optional: directory you want to download to>```
  -  If directory doesn't exists, then it will create one
  -  Ex:
```
python zenodo.py download 13960343 ./downloads
```

-  To upload
   -  Make sure you have an account in Zenodo
      -   You need to add your API token to the .env file
         -   Explained in the How to set up section above
   - The most efficient way is to store your dataset in a zip file
   -  Then use the command
    ```python zenodo.py upload <file name>.zip --title "<title of your dataset on zenodo>"```
      -   Ex:
```
python zenodo.py upload dataset.zip --title "My Dataset"
```
           
