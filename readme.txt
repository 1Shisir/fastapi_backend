1.First go to the project directory and open terminal

2.Type "python -m venv venv" ,the second venv is the name for virtual environment

3.For windows type "venv\Scripts\activate" for mac "source venv/bin/activate" .This will activate virtual environment.You may see (venv) at initial of the project directory.

4.Once activated venv,type "pip install -r requirements.txt" .This will install dependencies listed.

5.create a .env file in the root of the project and make adjustments
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=api-key
CLOUDINARY_API_SECRET=secret-key
DB_NAME=your-db-name
DB_USER=db-user
DB_PASS=password
DB_HOST=host    #mainly localhost
DB_PORT=port    #mainl  5432

       - you need to create a cloudinary id by signing in https://cloudinary.com/
       - cloudinary is used for stroing images

6.Then this is ready.So type "uvicorn main:app --reload
".This will start backend server.

7.Then visit' http://localhost:8000/docs' to access the Swagger UI for testing your API.