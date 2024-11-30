# MultiRoutes_FleetDeploy
Codes for paper ""
Project Title

This repository contains the official implementation of the paper "Liner Fleet Deployment and Empty Container Repositioning under Demand Uncertainty: A Robust Optimization Approach".
If you find this project useful, please ⭐Star the repository!

📄 Paper Information
Title: Liner Fleet Deployment and Empty Container Repositioning under Demand Uncertainty: A Robust Optimization Approach
Authors: Author Names
Published in: [Transportation Research Part B: Methodological]([Link to the paper](https://www.sciencedirect.com/science/article/pii/S0191261524002121))
Abstract:

This paper investigates a robust optimization problem concerning the integration of fleet deployment and empty container repositioning in a shipping line network, where a fleet of vessels is dispatched to transport both laden and empty containers, aiming to fulfill a predetermined set of requests over a defined time horizon. The sizes of customer demands are uncertain and are characterized by a budgeted uncertainty set. This study aims to ascertain the vessel types assigned to each shipping route, the routing of laden containers, and the repositioning of empty containers in a manner that minimizes the total cost.

🚀 Features
 Robust optimization
 Fleet deployment
 Empty container repositioning
 Shipping line network
📂 Project Structure
plaintext
├── data/                # Dataset and preprocessing scripts  
├── models/              # Model implementation  
├── utils/               # Utility functions and helper scripts  
├── results/             # Directory to store outputs/results  
├── README.md            # Project documentation  
├── requirements.txt     # Dependency list  
├── train.py             # Training script  
├── test.py              # Testing script  
└── LICENSE              # License information  
🛠️ Dependencies
Ensure the following environment setup:

Python Version: >= 3.8
Required Packages:
Install dependencies with the following command:
bash
pip install -r requirements.txt
📊 How to Run
1️⃣ Prepare the Data
Download the dataset mentioned in the paper and place it in the data/ directory.

2️⃣ Train the Model
Run the training script using:

bash
python train.py --config configs/train_config.json
3️⃣ Test the Model
Evaluate the model using the testing script:

bash
复制代码
python test.py --model_path checkpoints/best_model.pth
4️⃣ Visualize Results
Generate plots for the experimental results using:

bash
复制代码
python utils/plot_results.py
📚 Citation
If you use this code or model in your research, please cite our paper:

bibtex
复制代码
@article{xiang2024liner,
  title={Liner fleet deployment and empty container repositioning under demand uncertainty: A robust optimization approach},
  author={Xiang, Xi and Xu, Xiaowei and Liu, Changchun and Jia, Shuai},
  journal={Transportation Research Part B: Methodological},
  volume={190},
  pages={103088},
  year={2024},
  publisher={Elsevier}
}
📬 Contact
For any inquiries or issues, please feel free to open an issue or contact us via email: xuxw@bit.edu.cn
