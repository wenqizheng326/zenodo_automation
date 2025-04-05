# zenodo_automation

## How to set up for use
1. clone this repository via ssh
```git@github.com:wenqizheng326/zenodo_automation.git```
2. go to directory of the repository
   - check that you are in directory by using the command ```ls```
   - this should show you the files in you current directory
   - you are in the correct directory if you see the file called zenodo.py
     
3. create an .env file
   -  this is where you add your zenodo api token so you have access to more databases on zenodo
   -  use .env.example for what the file should look like
  
## Usage
- to search:
  - use the command
     ```python zenodo.py search _keywords you want to search by_```
    -  Ex: ```python zenodo.py search climate```
   
  - you can search via multiple keywords
    -  Ex: ```python zenodo.py search "machine learning" biology```
   
- to download:
  -  you need the database id
      -  this can be found in the URL endpoint
          -  Ex: if the URL is https://zenodo.org/record/13960343, then the id is 13960343
              -  the URL is produced when using search command
  -  use the command
  ```python zenodo.py download _database id_ _optional: directory you want to download to_```
  -  if directory doesn't exists then it will create one
  -  Ex: ```python zenodo.py download 123456 ./downloads```

-  to upload
  -  make sure you have an account in Zenodo, you need to add your API token to the .env file
    explained in the How to set up section above
  -  most efficient way is to store your dataset in a zip file
  -  then use the command
    ```python zenodo.py upload [_file name_.zip --title "_title of your dataset on zenodo_"```
