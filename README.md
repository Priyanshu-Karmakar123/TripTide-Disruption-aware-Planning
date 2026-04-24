# TripTide: A Benchmark for Adaptive Travel Planning under Disruptions
<img width="1127" height="435" alt="image" src="https://github.com/user-attachments/assets/3577ced0-7f89-40ee-ac35-3b8825e66f73" />
This repository contains the official implementation of TripTide, a newly proposed benchmark for analyzing LLM behavior under disruption-aware travel planning settings.

***
## 📢 Updates:
🏆 TripTide Paper got accepted at **ACL (findings), 2026** !!

***

## TripTide Overview
TripTide is a benchmark for evaluating how Large Language Models (LLMs) handle disruption-aware travel planning. It assesses itinerary revisions under real-world disruptions using metrics like Preservation of Intent, Responsiveness, and Adaptability (semantic, spatial, and sequential), along with LLM-as-a-Judge and human evaluation.

***

## Dataset Availability
TripTide comprises 11,058 disruption scenarios along with 1,000 GPT-4o-generated, disruption-aware annotated plans. To get access to our dataset and auxiliary databases, please send a request  to shreya[at]iitbbs.ac.in, abhikjana[at]iitbbs.ac.in, gmanish[at]microsoft.com and a24cs08008[at]iitbbs.ac.in .

  ### Note
  The requesting third party can:
  
      1. Download and use these deliverables for both research and commercial purposes,
      2. Modify them as desired, but include a citation to our work and include this README, and
      3. Use them internally only, without redistributing them to any other organization.

***

## How to Set-up the environment?

### Step 1: Install miniconda/anaconda in your system and check whether the Conda is installed using:
    conda --version
### Step 2: Initialize the environment by reproducing the TripTide conda setup and installing all required dependencies.
    conda env  create -f tcpt_env.yml -n triptide
    conda activate triptide

### Step 3: Download the database folder, then extract it inside the TripTide directory.

## How to Run?

---

The code base follows the structure like this:
### 1. Change the model name to your required model in run.sh file.
         bash run.sh
## Output normalization

---

Once you have generated all the travel plans correspondig to respective day's disruption make sure that the final itenaries are matched with the sample_evaluation_format prior to the evaluation. To improve reliability, we incorporate consistency checks that verify whether elements in the natural language itinerary are accurately aligned with their corresponding JSON fields, reducing discrepancies introduced during LLM-generated output transformation. We also encourage the exploration of alternative models and prompt design strategies to further strengthen the robustness and fidelity of the plan-to-structured-data conversion process.

***
 ## Evaluation

 The researchers can evaluate their generated plans using TripTide proposed evaluation metrics named as Preservation of Intent, Responsiveness, and Adaptability (semantic, spatial, and sequential). Additionally, TripTide also incorporate LLM-as-Judge evaluation scheme.

###  1. Preservation of Intent:
  We have extended TravelPlanner Evaluation [Script](https://github.com/OSU-NLP-Group/TravelPlanner/tree/main/evaluation) which includes Commensense (macro, micro), Hard Constraints (macro, micro) and Final Pass Rate to evaluate the generated plans.
###  2. Adaptability Metrics:
  ### a. Semantic Adapatability: Change the path of line number 114 and 115 with the annotated file and generated file path respectively.
          anno_path = "/scratch/anno_plan_5day.jsonl"
          revised_path = "/scratch/revised_5day.jsonl"
          ___
          cd evaluation
          python /scratch/persona_score.py
        
  ### b. Spatial Adaptabilty: Change the path of line number 69 and 70 with the annotated file and generated file path respectively.
        annotation_file = f"/your_path" #add the required path
        revised_file = f"/your_path"#add the required path
        ___
        cd evluation
        python /scratch/spatial_score.py 

  ### c. Sequential Adaptability: Change the path of line number 76 and 77 with the annotated file and generated file path respectively.
        annotation_file = f"/your_path" #add the required path
        revised_file = f"/your_path"#add the required path
        ___
        #set type 3day/5day/7day
        cd evaulation
        python /scratch/sequential_score.py --set_type 3day
### 3. Responsiveness:
      cd evaluation
      python /scratch/corresponding csv file 

##  BibTeX & Citation
  ### If you use our code in your research or wish to refer to our research paper, please use the following BibTeX entry.
    @misc{karmakar2025triptidebenchmarkadaptivetravel,
      title={TripTide: A Benchmark for Adaptive Travel Planning under Disruptions}, 
      author={Priyanshu Karmakar and Soumyabrata Chaudhuri and Shubhojit Mallick and Manish Gupta and Abhik Jana and Shreya Ghosh},
      year={2025},
      eprint={2510.21329},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2510.21329}, 
}

## Acknowledgement
This repository is partially built based on [TravelPlanner](https://github.com/OSU-NLP-Group/TravelPlanner?tab=readme-ov-file) and [TripCraft](https://github.com/Soumyabrata2003/TripCraft?tab=readme-ov-file). Sincere thanks to their wonderful work.
### Additionally, the annotation of the dataset would not be possible without the collective effort of the following people (in alphabetical order):
    Ananya Dash, Aniket Rouniyar, Anindya Kartik, Anurag Sahu, Aryaneel Bhaduri, Avinaba Chakraborty, B K Bandana, Biswadeep Chakraborty, Biswajit Polai, Borru Vijay Sai, C Dattasai Aditya Amman, D. Youktasri, Debansi Patnaik, Deepon Halder, Devang Bordoloi, Etcharla Revanth Rao, Gaurav Kumar Jha, Gyanaditya Pattanaik, Harshit Goel, Hiraish Kumar, Jaya Sahithya Vege, Joy Mukhopadhyay, Kavya Dixit, Kommuru Jayasurya, Kunal Nandeshwar, M. Kalyan Ram, Madhav Ramanathan, Mansi Mehta, Meena Kalyani, N M Amlan, Omprakash Rout, P Jayanth Vinay, Piyush Kumar Gupta, Priyambada Acharya, Pujarani Guru, Riddhi Mandal, Rohith Marpina, Rohan Karn, Sadiq Khan, Sagar Bisht, Saumay Tyagi, Sayoni Chakraborty, Snehanshu Pal, Snehal Tripathy, Soham Roy, Soumalya Banik, Soumya Ranjan Nayak, Sourabh Patil, Vaishnavi Kanukuntla, Vishal Raj, Vytla Rakesh Mohan
