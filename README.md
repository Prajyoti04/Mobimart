# MobiMart Inventory & Allocation Optimizer

## End-to-end decision-support prototype

Pipeline:
1. Data generation + validation
2. Store profiling and segmentation
3. Demand forecasting / backtesting
4. Inventory allocation + naive baseline
5. EOL detection
6. Markdown + successor transition
7. Store-level transfer recommendations
8. Six-week stochastic simulation
9. Interactive Streamlit dashboard

## Run the dashboard

Open a terminal in the `dashboard` folder:

```bash
pip install -r ../requirements.txt
streamlit run app.py
```

## Key conclusion

The optimizer improves allocation efficiency versus the naive baseline, while
the stress-test simulation shows that inventory availability becomes the dominant
constraint under high-demand and festive conditions.

## Important prototype limitations

Actual on-hand inventory, supplier lead times, purchase orders, transfer logistics
constraints, and realized future demand are not included in the supplied data.
Where required, the project uses explicit planning assumptions rather than
presenting those values as observed facts.

## 🚀 Live Demo

The MobiMart Inventory & Allocation Optimizer is deployed and available here:

🔗 **Live Application:** [MobiMart Optimizer](https://mobimart-ancxxfiq6nelx6jhible6q.streamlit.app/)
