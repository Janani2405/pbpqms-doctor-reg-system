from flask import Flask, redirect, render_template, request, jsonify, url_for
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Oracle DB connection
connection_string = (
    f"DRIVER={{Oracle in instantclient_23_6}};"
    f"DBQ={os.getenv('DBQ', 'localhost/XE')};"
    f"UID={os.getenv('DB_USER', 'system')};"
    f"PWD={os.getenv('DB_PASSWORD', '')};"
)
connection = pyodbc.connect(connection_string)


# Routes
@app.route('/', methods=['GET', 'POST'])
def authenticity_form():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return jsonify({'error': 'Username and password are required.'}), 400

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT username, password, alternate_password FROM Users WHERE username = ?", (username,))
                user = cursor.fetchone()

                if not user:
                    return jsonify({'error': 'User does not exist.'}), 404

                db_username, db_password, alt_password = user
                if password == db_password or password == alt_password:
                    return redirect(url_for('doc_reg'))  # Redirects to /doc_reg
                else:
                    return jsonify({'error': 'Incorrect password.'}), 403
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('authenticity_form.html')

@app.route('/doc_reg', methods=['GET', 'POST'])
def doc_reg():
    print("Request received in doc_reg")
    print("Form data:", request.form)
    if request.method == 'GET':
        return render_template('doc_reg.html')

    data = request.form.to_dict()
    action = data.get('action')
    doctor_id = data.get('doctor-id')

    if not doctor_id:
        return jsonify({'error': 'Doctor ID is required.'})

    try:
        with connection.cursor() as cursor:
            if action =='Save':
                # Check if the record exists in the Buffer table
                cursor.execute("SELECT is_committed FROM Buffer WHERE doctor_id = ?", (doctor_id,))
                record = cursor.fetchone()

                if record:
                    if record[0] == 1:  # Check if the record is committed
                        return jsonify({'error': 'Committed records cannot be updated or inserted.'})

                    # Update existing record in Buffer for Save or Update actions
                    
                    cursor.execute("""
                        UPDATE Buffer
                        SET doctor_name = ?, qualification = ?, specialization = ?,
                            channel_fee = ?, age = ?, gender = ?, room_no = ?
                        WHERE doctor_id = ?
                    """, (
                        data['doctor-name'], data['qualification'], data['specialization'],
                        data['channel-fee'], data['age'], data['gender'], data['room-no'], doctor_id
                    ))
                    connection.commit()
                    return jsonify({'message': 'Record updated successfully in buffer.'})
                else:
                    # Insert new record into Buffer for Insert or Save actions
                    cursor.execute("""
                        INSERT INTO Buffer (doctor_id, doctor_name, qualification, specialization,
                                            channel_fee, age, gender, room_no, is_committed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """, (
                        doctor_id, data['doctor-name'], data['qualification'], data['specialization'],
                        data['channel-fee'], data['age'], data['gender'], data['room-no']
                    ))
                    connection.commit()
                    return jsonify({'message': 'New record inserted successfully into buffer.'})
                
            if action == 'SaveSingleField':
                # Ensure exactly one additional field is provided along with Doctor ID
                update_fields = {key: value for key, value in data.items() if key not in ['doctor-id', 'action'] and value}

                if len(update_fields) != 1:
                    return jsonify({'error': 'Exactly one additional field must be provided along with Doctor ID.'}), 400

                field_name, field_value = list(update_fields.items())[0]

                # Validate the field
                field_mapping = {
                    'doctor-name': 'doctor_name',
                    'qualification': 'qualification',
                    'specialization': 'specialization',
                    'channel-fee': 'channel_fee',
                    'age': 'age',
                    'gender': 'gender',
                    'room-no': 'room_no',
                }
                db_field_name = field_mapping.get(field_name)
                if not db_field_name:
                    return jsonify({'error': f'Invalid field: {field_name}'}), 400

                # Check if the record exists in the Buffer table
                cursor.execute("SELECT is_committed FROM Buffer WHERE doctor_id = ?", (doctor_id,))
                record = cursor.fetchone()

                if not record:
                    return jsonify({'error': 'Record not found in buffer.'}), 404

                if record[0] == 1:  # Committed record
                    return jsonify({'error': 'Committed records cannot be updated.'}), 403

                # Update the specific field
                cursor.execute(f"UPDATE Buffer SET {db_field_name} = ? WHERE doctor_id = ?", (field_value, doctor_id))
                connection.commit()
                return jsonify({'message': f'{field_name.replace("_", " ").capitalize()} updated successfully in buffer.'})

            
            elif action == 'Commit':
                # Check if the record exists in the Buffer table
                cursor.execute("SELECT is_committed FROM Buffer WHERE doctor_id = ?", (doctor_id,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({'error': 'Record not found in buffer.'}), 404

                if result[0] == 1:  # is_committed flag
                    return jsonify({'error': 'Record is already committed.'}), 403

                # Commit to main table
                cursor.execute("""
                    INSERT INTO Doctors (doctor_id, doctor_name, qualification, specialization,
                                         channel_fee, age, gender, room_no)
                    SELECT doctor_id, doctor_name, qualification, specialization,
                           channel_fee, age, gender, room_no
                    FROM Buffer WHERE doctor_id = ?
                """, (doctor_id,))
                cursor.execute("UPDATE Buffer SET is_committed = 1 WHERE doctor_id = ?", (doctor_id,))
                connection.commit()
                return jsonify({'message': 'Record committed successfully.'})
            
            elif action == 'Delete':
                # Delete logic
                cursor.execute("SELECT is_committed FROM Buffer WHERE doctor_id = ?", (doctor_id,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({'error': 'Record not found in buffer.'})

                if result[0] == 1:
                    return jsonify({'error': 'Committed records cannot be deleted.'})

                cursor.execute("DELETE FROM Buffer WHERE doctor_id = ?", (doctor_id,))
                connection.commit()
                return jsonify({'message': 'Record deleted successfully.'})
            

            elif action == 'Previous':
                # Fetch the previous record
                cursor.execute("""
                    SELECT * FROM Buffer
                    WHERE doctor_id < ?
                    ORDER BY doctor_id DESC
                    FETCH FIRST 1 ROWS ONLY
                """, (doctor_id,))
                record = cursor.fetchone()

                if not record:
                    return jsonify({'error': 'This is the first record.'})

                # Return the previous record as a JSON response
                return jsonify({
                    'doctor_id': record[0],
                    'doctor_name': record[1],
                    'qualification': record[2],
                    'specialization': record[3],
                    'channel_fee': record[4],
                    'age': record[5],
                    'gender': record[6],
                    'room_no': record[7]
                })

            elif action == 'Next':
                # Fetch the next record
                cursor.execute("""
                    SELECT * FROM Buffer
                    WHERE doctor_id > ?
                    ORDER BY doctor_id ASC
                    FETCH FIRST 1 ROWS ONLY
                """, (doctor_id,))
                record = cursor.fetchone()

                if not record:
                    return jsonify({'error': 'This is the last record.'})

                # Return the next record as a JSON response
                return jsonify({
                    'doctor_id': record[0],
                    'doctor_name': record[1],
                    'qualification': record[2],
                    'specialization': record[3],
                    'channel_fee': record[4],
                    'age': record[5],
                    'gender': record[6],
                    'room_no': record[7]
                })
            
            if action == 'Insert':
                # Check if the record is committed
                cursor.execute("SELECT is_committed FROM Buffer WHERE doctor_id = ?", (doctor_id,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({'error': 'Record not found in buffer.'})

                if result[0] == 1:  # is_committed flag
                    return jsonify({'error': 'Committed records cannot be updated or inserted.'})

                # Allow updating or inserting by enabling the fields in the frontend
                return jsonify({'message': 'Fields enabled for updating/inserting.'})

            elif action == 'Update':
                # Fetch is_committed status from the database
                cursor.execute("SELECT is_committed FROM Buffer WHERE doctor_id = ?", (doctor_id,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({'error': 'Record not found in buffer.'})

                is_committed = bool(result[0])
                print(f"Record {doctor_id} isCommitted: {is_committed}")  # Debug log

                return jsonify({'isCommitted': is_committed})

            elif action == 'Fetch':
                # Fetch the record from the Buffer table
                try:
                    cursor.execute("""
                        SELECT * FROM Buffer WHERE doctor_id = ?
                    """, (doctor_id,))
                    record = cursor.fetchone()

                    if not record:
                        return jsonify({'error': 'Record not found in buffer.'})

                    # Return the record as a JSON response
                    return jsonify({
                        'doctor_id': record[0],
                        'doctor_name': record[1],
                        'qualification': record[2],
                        'specialization': record[3],
                        'channel_fee': record[4],
                        'age': record[5],
                        'gender': record[6],
                        'room_no': record[7]
                    })
                except Exception as e:
                    return jsonify({'error': str(e)}), 500


            
    except Exception as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/view_records', methods=['GET'])
def view_records():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Doctors")
            doctors = cursor.fetchall()

        doctors_list = [
            {
                'doctor_id': row[0],
                'doctor_name': row[1],
                'qualification': row[2],
                'specialization': row[3],
                'channel_fee': row[4],
                'age': row[5],
                'gender': row[6],
                'room_no': row[7]
            }
            for row in doctors
        ]
        return render_template('view_records.html', records=doctors_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/new_user', methods=['GET', 'POST'])
def new_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        alt_password = request.form['alt-password']
        user_type = request.form['user-type']

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO Users (username, password, alternate_password, usertype)
                    VALUES (?, ?, ?, ?)
                """, (username, password, alt_password, user_type))
                connection.commit()
            return jsonify({'message': 'User successfully created!'}), 200
        except pyodbc.IntegrityError:
            return jsonify({'error': 'Username already exists.'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('new_user.html')

@app.route('/change_pwd', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        username = request.form['username']
        current_password = request.form['current-password']
        new_password = request.form['new-password']

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT password, alternate_password FROM Users WHERE username = ?
                """, (username,))
                result = cursor.fetchone()

                if result is None:
                    return jsonify({'error': 'User not found.'}), 404

                db_password, alt_password = result

                if current_password == db_password:
                    cursor.execute("""
                        UPDATE Users SET password = ? WHERE username = ?
                    """, (new_password, username))
                elif current_password == alt_password:
                    cursor.execute("""
                        UPDATE Users SET alternate_password = ? WHERE username = ?
                    """, (new_password, username))
                else:
                    return jsonify({'error': 'Incorrect current password or alternate password.'}), 403

                connection.commit()
                return jsonify({'message': 'Password updated successfully!'}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('change_pwd.html')

@app.route('/view_users', methods=['GET'])
def view_users():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Users")
            users = cursor.fetchall()

        users_list = [
            {
                'username': row[0],
                'password': row[1],
                'alternate_password': row[2],
                'user_type': row[3],
            }
            for row in users
        ]
        return render_template('view_users.html', users=users_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@app.route('/fetch_options', methods=['GET'])
def fetch_options():
    field = request.args.get('field')
    if not field:
        return jsonify({'error': 'Field name is required'}), 400

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT DISTINCT {field} FROM Buffer")
            options = [row[0] for row in cursor.fetchall()]
        return jsonify(options), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/view_buffer', methods=['GET'])
def view_buffer():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Buffer")
            buffer_records = cursor.fetchall()

        records_list = [
            {
                'doctor_id': row[0],
                'doctor_name': row[1],
                'qualification': row[2],
                'specialization': row[3],
                'channel_fee': row[4],
                'age': row[5],
                'gender': row[6],
                'room_no': row[7],
                'is_committed': bool(row[8]),
            }
            for row in buffer_records
        ]
        return render_template('buffer_table.html', records=records_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/fetch_highest_doctor_id', methods=['GET'])
def fetch_highest_doctor_id():
    try:
        with connection.cursor() as cursor:
            # Query to get the highest Doctor ID (string comparison works since IDs are zero-padded)
            cursor.execute("SELECT MAX(doctor_id) FROM Buffer")  # Adjust table name if needed
            result = cursor.fetchone()
            highest_id = result[0] if result and result[0] else "D000"  # Default to D000 if no records
        return jsonify({'highest_id': highest_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
