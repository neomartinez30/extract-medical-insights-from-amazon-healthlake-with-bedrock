#!/bin/bash

# Start Streamlit instances for each route
streamlit run app_fhir.py /sidebar --server.port 8510 &
streamlit run app_fhir.py /summary --server.port 8511 &
streamlit run app_fhir.py /chat --server.port 8512 &
streamlit run app_fhir.py /fhir --server.port 8513 &

# Wait for all background processes
wait
