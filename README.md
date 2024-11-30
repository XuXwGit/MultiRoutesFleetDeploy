# **Multi Routes Fleet Deployment**  
This repository contains the official implementation of the paper "Liner Fleet Deployment and Empty Container Repositioning under Demand Uncertainty: A Robust Optimization Approach".

If you find this project useful to your research, please ⭐Star the repository and 📚Cite this paper!

---

## 📄 **Paper Information**  
**Title:** Liner Fleet Deployment and Empty Container Repositioning under Demand Uncertainty: A Robust Optimization Approach

**Authors:** Xi Xiang, Xw Xu, Changchun Liu, Shuai Jia

**Published in:** [Transportation Research Part B: Methodological]([Link to the paper](https://www.sciencedirect.com/science/article/pii/S0191261524002121))

**Abstract:**  
> This paper investigates a robust optimization problem concerning the integration of fleet deployment and empty container repositioning in a shipping line network, where a fleet of vessels is dispatched to transport both laden and empty containers, aiming to fulfill a predetermined set of requests over a defined time horizon. The sizes of customer demands are uncertain and are characterized by a budgeted uncertainty set. This study aims to ascertain the vessel types assigned to each shipping route, the routing of laden containers, and the repositioning of empty containers in a manner that minimizes the total cost.

---

## 🚀 **Features**  
 Maritime shipping, Fleet deployment, Empty container repositioning, Demand uncertainty, Robust optimization

---

## 📂 **Project Structure**  
```plaintext
├── data/                # Dataset
├── src/                 # Core algorithm part of this Project  
├── README.md            # Project documentation  
└── LICENSE              # License information
```

## 🛠️ Dependencies
Ensure the following environment setup: Cplex 12.10, Java 8

## 📊 How to Run
To run this project, run the following codes:
```bash
java -cp [classpath] multi.Main [Instance] [Experiment] [RootPath] [MIPGapLimit] [RandomSeed] [BudgetCoefficient] [UncertainDegree] [Flag]
```

## 📚 Citation
If you use this code or model in your research, please cite our paper:
```bibtex
@article{xiang2024liner,
  title={Liner fleet deployment and empty container repositioning under demand uncertainty: A robust optimization approach},
  author={Xiang, Xi and Xu, Xiaowei and Liu, Changchun and Jia, Shuai},
  journal={Transportation Research Part B: Methodological},
  volume={190},
  pages={103088},
  year={2024},
  publisher={Elsevier}
}
```

## 📬 Contact
For any inquiries or issues, please feel free to open an issue or contact us via email: xuxw@bit.edu.cn
