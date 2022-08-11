import mriqa_marker_objects
import subprocess
import glob
from datetime import datetime
import os
from os import path
import json
import csv 
from configparser import ConfigParser



config = ConfigParser()
config.read('hep_rating-tool_config.ini')


output = 'MRI_rating_record/'
types = [config['settings']['input_images'] + '**/*.nii', config['settings']['input_images']+'**/*.nii.gz']
files = []
for type in types: 
    files_list = glob.glob(type, recursive = True)
    files += files_list

print(len(files))

now = datetime.now()
time_str = now.strftime("%d-%m-%Y_%H:%M:%S")
date = now.strftime("%d-%m-%Y_%H:%M")



#check if output directory exists
if path.exists("MRI_rating_record/") == False:
    os.mkdir("MRI_rating_record/")
    print("\n\nDirectory 'MRI_rating_record' created! Your ratings will be stored here. \n\n")

#instantiate simpleDB class and the location of the output JSON files 
db = mriqa_marker_objects.SimpleDB(output)

ratings_table = None
output_db_name = None
locations = []

session_tracker = input("Resume a previous session? \n1 - New session\n2 - Resume previous sessions\nSelection: ")

#STARTING A NEW FILE 
if session_tracker == '1':

    #creates or directs to a table object that maps to JSON file 
    ratings_table = db.table("MRIrate_session-"+time_str)
    #creates a .JSON file named based on date  
    output_db_name = "MRI_rating_record/MRIrate_session-{}.json".format(time_str)

#RESUMING AN EXISTING FILE 
if session_tracker == '2':
    
    #create a list of all existing .json files: list items will be displayed as potential sessions to resume
    json_list = []
    #location of .json files of interest if resuming session
    for item in os.listdir(output):
        if '.json' in item:
            json_list.append(item.replace('.json', ''))

    #index the filepaths in the JSON files so they can be called later on, ajust by one for python 0 index     
    counter = 1
    for item in json_list:
        #print the json file name with a corresponding index value
        print (str(counter) +'. '+ str(item)) 
        counter += 1
    
    #check if there are no .json files to resume
    if counter == 1:
        input('No sessions to resume. Press Enter to quit')
        quit()

    #locate the correct file by translating to index starting at 0 (files)
    index = input("Enter session number to resume: ")
    #Correct the indexing values per python 0-index 
    list_index = int(index)-1
    
    #check that a valid session has been chosen 
    if not 0 <= list_index <= len(json_list)-1:
        input('Invalid session. Press Enter to quit')
        quit()

    #creates variable based on chosen file ID
    output_db_name = json_list[list_index]

    #open a ratings table using simple db in the selected file 
    ratings_table = db.table(output_db_name)

    #Open JSON file
    json_filename = open('MRI_rating_record/' + output_db_name + '.json')

    #variable that returns JSON object as dictionary 
    json_dict = json.load(json_filename)
    #create a list of all filepaths already appearing in the JSON file 
    # for loop will check this list before opening ITKsnap  
    locations = [json_entry['filepath'] for json_entry in json_dict]
    output_db_name = 'MRI_rating_record/' + output_db_name + '.json'

try:
    for filepath in files:

        # Check if the filepath matches any of the entries in the 'filepath' key
        if filepath in locations:
            continue
        
        # Dict to hold all ratings (main rating and artifacts)
        ratings = { 'rating': '',
                    'S': '',
                    'M': '',
                    'F': '', }
        
        snap = subprocess.Popen(['itksnap', filepath], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        names = filepath.split('/')
        labels = input("\nFile: {}\n\nPress enter for a correctly labelled file (T1,T2, FLAIR).\nOtherwise type the correct label: ".format(names[-1]))
        print('\n\nEnter rating for overall image quality \n1. Very Poor \n2. Suboptimal \n3. Acceptable \n4. Above Average \n5. Excellent\n\n')
        while True:
            try:
                ratings['rating'] = int(input("Rating (1 to 5): "))
                if not ratings['rating'] in range(1,6):  
                    raise ValueError
                break
            except ValueError:
                print("Rating not valid, enter a number from 1-5")

        
        # while any of these variables are '' the loop can continue 
        while '' in ratings.values():
            #aesthetic spacing
            print('\n') 
            
            while True:
                print('Enter letter to rate artifact or hit enter to continue. \n\nM - MOTION \nS - SUSCEPTIBILITY\nF - FLOW/GHOSTING\n\n')    
                artifact = input("Artifact: ").upper()

                if not artifact:
                    break
                if artifact in ['S', 'M', 'F']:
                    break
                else: 
                    print("\n\nInvalid choice")
            if not artifact:
                break
            

            while True:
                try: 
                    print('1 - Severe, 2 - Moderately Severe, 3 - Moderate, 4 - Mild, 5 - None')
                    artifact_rating = int(input("Rating: "))
                    if not artifact_rating in range(1,6):  
                        raise ValueError
                    break
                #catch valueerror that will crash program
                except ValueError:
                    print("\nInvalid choice, enter number from 1-5\n")
            
            ratings[artifact] = artifact_rating


        ratings_table.insert(filepath= filepath, rating=ratings['rating'], date=date, susceptibility=ratings['S'], motion=ratings['M'], flow=ratings['F'], label=labels)
        mriqa_marker_objects.kill_process()
        
except KeyboardInterrupt:
    print('\n\n+----------------------------+\n\nSession Ended\n\n+----------------------------+')
    pass 


#Open JSON file
json_file = open(output_db_name)
print('\n\nTwo files generated (.csv, .json): ' + output_db_name.replace('.json', '') + '\n\n')
#returns JSON object as dictionary 
json_dict = json.load(json_file)

#open empty file for writing
CSV_ratings = open(output_db_name.replace('.json', '.csv'), 'w')
#field name information 
field_info = ['filepath','rating', 'date', 'susceptibility', 'motion', 'flow', 'label']
# create the csv writer object
csv_writer = csv.DictWriter(CSV_ratings, fieldnames= field_info)

count = 0
for line in json_dict:
    if count == 0:
        #write headers as no entries have been made 
        #header = ('filepath','rating','date')
        csv_writer.writeheader()
        count += 1
        csv_writer.writerows(json_dict)
    #write json_filename from JSON to CSV
CSV_ratings.close()
