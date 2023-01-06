FROM  python:3.8
MAINTAINER UNP, https://unp.education
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8501
CMD streamlit run get_house_price.py

