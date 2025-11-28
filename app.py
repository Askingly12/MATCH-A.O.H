from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector # CORRECCIÓN: Conector de MySQL importado
from mysql.connector import errorcode
from datetime import timedelta
from functools import wraps
# Ya no necesitamos os, plotly, o psycopg2

app = Flask(__name__)
# ¡IMPORTANTE! Cambia esta clave en un entorno de producción.
app.secret_key = 'tu_clave_secreta_aqui' 
app.permanent_session_lifetime = timedelta(minutes=30)

# --- Configuración de MySQL (PARA PYTHONANYWHERE) ---
# **DEBES REEMPLAZAR ESTOS VALORES EN EL PASO 4 DEL DESPLIEGUE**
DB_CONFIG = {
    'user': 'Askingly',             # Tu usuario de PythonAnywhere
    'password': 'lyfresita',     # La contraseña que definas para MySQL en PA
    'host': 'Askingly.mysql.pythonanywhere-services.com',         # El hostname largo de PA (ej. usuario.mysql.pythonanywhere-services.com)
    'database': 'consumo_de_energia_db'       # El nombre de la DB (ej. usuario$default)
}

def get_db_connection():
    """Establece la conexión a la base de datos MySQL."""
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        return cnx
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("❌ ERROR DE CONEXIÓN: Usuario o contraseña de MySQL incorrectos.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"❌ ERROR DE CONEXIÓN: La base de datos {DB_CONFIG['database']} no existe.")
        else:
            print(f"❌ ERROR DE CONEXIÓN GENERAL: {err}")
        return None

# --- Decorador de Autenticación (Mantener) ---

def login_required(f):
    """Asegura que el usuario esté logeado para acceder a ciertas rutas."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Funciones de Lógica de Negocio (Mantener) ---

def clasificar_consumo(kwh, tipo_usuario):
    if tipo_usuario == 'casa':
        if kwh < 150:
            return 'BAJO'
        elif kwh <= 450:
            return 'MEDIO'
        else:
            return 'ALTO'
    elif tipo_usuario == 'empresa':
        if kwh < 800:
            return 'BAJO'
        elif kwh <= 2500:
            return 'MEDIO'
        else:
            return 'ALTO'
    return 'INDETERMINADO'

def obtener_problemas_y_soluciones(clasificacion, antiguedad):
    problemas = []
    soluciones = []

    if clasificacion == 'ALTO':
        problemas.append("Consumo energético muy elevado (Revisar facturación tarifaria).")
        soluciones.append("Revisar aparatos de alto consumo (ej. calentadores, A/C) y su uso programado.")
    
    if clasificacion == 'MEDIO':
        problemas.append("Consumo dentro del rango aceptable, pero existe potencial de ahorro.")
        soluciones.append("Optimizar el uso de iluminación y equipos durante horas pico.")

    if antiguedad > 5:
        problemas.append("Antigüedad de equipos que implica baja eficiencia (mayor de 5 años).")
        soluciones.append("Considerar la sustitución de electrodomésticos o luminarias viejas por modelos de alta eficiencia.")

    if not problemas and clasificacion == 'BAJO':
        problemas.append("Consumo optimizado. Mantenimiento preventivo sugerido.")
        soluciones.append("Continuar con buenas prácticas y monitoreo mensual para mantener el rendimiento.")
    elif not problemas:
        problemas.append("Datos insuficientes para diagnóstico preciso.")
        soluciones.append("Proporcionar más registros para un análisis completo.")

    return problemas, soluciones

# --- Rutas de Navegación y Autenticación ---

@app.route('/', methods=['GET'])
def home():
    if 'user_id' in session:
        return redirect(url_for('cuestionario'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'] 
        
        cnx = get_db_connection()
        if cnx:
            # Usar cursor(dictionary=True) para MySQL
            cursor = cnx.cursor(dictionary=True) 
            query = "SELECT id, nombre, email, tipo_usuario, password FROM usuarios WHERE email = %s AND password = %s"
            cursor.execute(query, (email, password))
            user = cursor.fetchone()
            cursor.close()
            cnx.close()

            if user:
                session.permanent = True
                session['user_id'] = user['id']
                session['user_name'] = user['nombre']
                session['user_type'] = user['tipo_usuario']
                flash(f'¡Bienvenido de nuevo, {user["nombre"]}!', 'success')
                return redirect(url_for('cuestionario')) 
            else:
                flash('Credenciales incorrectas.', 'error')
                
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))


@app.route('/registro/<tipo_usuario>', methods=['GET', 'POST'])
def registro(tipo_usuario):
    if tipo_usuario not in ['casa', 'empresa']:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']

        cnx = get_db_connection()
        if cnx:
            cursor = cnx.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('El email ya está registrado.', 'error')
                cursor.close()
                cnx.close()
                return redirect(url_for('registro', tipo_usuario=tipo_usuario))

            query = "INSERT INTO usuarios (nombre, email, password, tipo_usuario) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nombre, email, password, tipo_usuario))
            cnx.commit()
            cursor.close()
            cnx.close()
            
            flash('¡Registro exitoso! Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))

    titulo_display = "Tu Casa o Local" if tipo_usuario == 'casa' else "Tu Empresa"
    return render_template('registro.html', tipo_usuario=tipo_usuario, titulo_display=titulo_display)


@app.route('/cuestionario', methods=['GET', 'POST'])
@login_required
def cuestionario():
    """Muestra el formulario de consumo específico y procesa su envío."""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    titulo = "Registro de Consumo - Hogar/Local" if user_type == 'casa' else "Registro de Consumo - Empresa"

    if request.method == 'POST':
        cnx = None
        try:
            # 1. Datos comunes y de clasificación
            consumo_kwh = float(request.form['consumo_kwh'])
            
            # Cálculo de antigüedad para el diagnóstico general (antiguedad_equipo)
            antiguedad_equipo_general = 0
            if user_type == 'casa':
                antiguedad_str = request.form['antiguedad_instalacion_c']
                if antiguedad_str == 'antigua': antiguedad_equipo_general = 16
                elif antiguedad_str == 'media': antiguedad_equipo_general = 10
                else: antiguedad_equipo_general = 2
            elif user_type == 'empresa':
                antiguedad_equipo_general = int(request.form['antiguedad_instalacion_e'])
                # Captura del nuevo campo de tamaño de empresa
                tipo_empresa_tamano = request.form['tipo_empresa_tamano']
            else:
                tipo_empresa_tamano = 'N/A'

            clasificacion = clasificar_consumo(consumo_kwh, user_type)
            
            cnx = get_db_connection()
            if cnx:
                cursor = cnx.cursor()
                
                # 2. Guardar datos específicos en la tabla correspondiente
                if user_type == 'casa':
                    query = """INSERT INTO registro_casa (user_id, fecha, consumo_kwh, gasto_mxn, antiguedad_equipo, clasificacion,
                                tipo_vivienda, superficie_m2, conoce_consumo, medidor_inteligente, tipo_focos, horas_iluminacion,
                                cant_refrigeradores, tipo_refrigerador, uso_lavadora, uso_secadora, cant_tv, horas_tv, cant_pc, horas_pc,
                                cant_ac, uso_ac_horas, tipo_calentador, desconectar_aparatos, modo_standby, usos_inteligentes,
                                antiguedad_instalacion_c, mantenimiento_c, num_habitantes) 
                                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    
                    params = (
                        user_id, consumo_kwh, 0.0, antiguedad_equipo_general, clasificacion,
                        request.form['tipo_vivienda'], int(request.form['superficie_m2']), request.form['conoce_consumo'], request.form['medidor_inteligente'], request.form['tipo_focos'], float(request.form['horas_iluminacion']),
                        int(request.form['cant_refrigeradores']), request.form['tipo_refrigerador'], float(request.form['uso_lavadora']), float(request.form['uso_secadora']), int(request.form['cant_tv']), float(request.form['horas_tv']), int(request.form['cant_pc']), float(request.form['horas_pc']),
                        int(request.form['cant_ac']), float(request.form['uso_ac_horas']), request.form['tipo_calentador'], request.form['desconectar_aparatos'], request.form['modo_standby'], request.form['usos_inteligentes'],
                        request.form['antiguedad_instalacion_c'], request.form['mantenimiento_c'], int(request.form['num_habitantes'])
                    )
                    cursor.execute(query, params)
                
                elif user_type == 'empresa':
                    query = """INSERT INTO registro_empresa (user_id, fecha, consumo_kwh, gasto_mxn, antiguedad_equipo, clasificacion,
                                tipo_empresa, num_empleados, tamano_m2, horario_operacion, medidor_inteligente_e, tarifa_electrica,
                                areas_alto_consumo, tipo_luminarias, cant_lamparas, sensores_presencia, num_computadoras, horas_pc_uso,
                                monitores_puesto, impresoras_uso, standby_laboral, usa_maquinaria, maquinas_potencia, servidores_247,
                                refrigeracion_industrial, cant_ac_e, horas_operacion_ac, sistemas_ac, apagan_al_final, politicas_ahorro,
                                monitoreo_areas, antiguedad_instalacion_e, mantenimiento_reciente_e, auditoria_energetica) 
                                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                                
                    params = (
                        user_id, consumo_kwh, 0.0, antiguedad_equipo_general, clasificacion,
                        # Usamos tipo_empresa_tamano aquí:
                        tipo_empresa_tamano, int(request.form['num_empleados']), int(request.form['tamano_m2']), float(request.form['horario_operacion']), request.form['medidor_inteligente_e'], request.form['tarifa_electrica'],
                        request.form['areas_alto_consumo'], request.form['tipo_luminarias'], int(request.form['cant_lamparas']), request.form['sensores_presencia'], int(request.form['num_computadoras']), float(request.form['horas_pc_uso']),
                        int(request.form['monitores_puesto']), request.form['impresoras_uso'], int(request.form['standby_laboral']), request.form['usa_maquinaria'], request.form['maquinas_potencia'], int(request.form['servidores_247']),
                        request.form['refrigeracion_industrial'], int(request.form['cant_ac_e']), float(request.form['horas_operacion_ac']), request.form['sistemas_ac'], request.form['apagan_al_final'], request.form['politicas_ahorro'],
                        request.form['monitoreo_areas'], int(request.form['antiguedad_instalacion_e']), request.form['mantenimiento_reciente_e'], request.form['auditoria_energetica']
                    )
                    cursor.execute(query, params)

                registro_id = cursor.lastrowid
                cnx.commit()
                cursor.close()
                cnx.close()
                
                flash('Registro guardado exitosamente.', 'success')
                return redirect(url_for('diagnostico', registro_id=registro_id, tipo=user_type))

        except ValueError:
            flash('Error: Asegúrate de que todos los campos numéricos contengan números válidos.', 'error')
            if cnx: cnx.close()
            return redirect(url_for('cuestionario'))
        except Exception as e:
            flash(f'Error al guardar en la base de datos: {e}', 'error')
            if cnx: cnx.close()
            return redirect(url_for('cuestionario'))

    # Se pasa el nuevo campo 'tipo_empresa_tamano' para el selector de tamaño en el HTML
    return render_template('cuestionario.html', titulo_apartado=titulo, user_type=user_type)


@app.route('/diagnostico/<tipo>/<int:registro_id>', methods=['GET'])
@login_required
def diagnostico(tipo, registro_id):
    """Muestra el diagnóstico y soluciones, con cálculo simple de promedio."""
    user_id = session.get('user_id')
    user_type = session.get('user_type')

    if tipo != user_type:
        flash('Acceso denegado al tipo de registro.', 'error')
        return redirect(url_for('cuestionario'))
        
    cnx = get_db_connection()
    if cnx:
        cursor = cnx.cursor(dictionary=True)
        
        table = 'registro_casa' if tipo == 'casa' else 'registro_empresa'
        query = f"SELECT * FROM {table} WHERE id = %s AND user_id = %s"
        cursor.execute(query, (registro_id, user_id))
        registro = cursor.fetchone()
        
        if not registro:
            flash('Registro no encontrado o no pertenece a tu cuenta.', 'error')
            cursor.close()
            cnx.close()
            return redirect(url_for('cuestionario'))

        history_query = f"SELECT consumo_kwh FROM {table} WHERE user_id = %s AND id != %s ORDER BY fecha DESC LIMIT 5"
        cursor.execute(history_query, (user_id, registro_id)) 
        historial_consumos = cursor.fetchall()
        
        cursor.close()
        cnx.close()

        try:
            clasificacion_actual = str(registro['clasificacion'])
            antiguedad = int(registro['antiguedad_equipo'])
            
            problemas, soluciones = obtener_problemas_y_soluciones(clasificacion_actual, antiguedad)
        except Exception as e:
            problemas = [f"Error al calcular diagnóstico: {e}"]
            soluciones = ["Revisar el formato de los datos almacenados en MySQL."]
            
        # Calcular consumo promedio para mostrar solo el número
        consumo_promedio = 0 
        if historial_consumos:
            consumos_pasados = [float(item['consumo_kwh']) for item in historial_consumos]
            consumo_promedio = sum(consumos_pasados) / len(consumos_pasados)
        
        return render_template('diagnostico.html', 
                               registro=registro, 
                               tipo=tipo, 
                               problemas=problemas, 
                               soluciones=soluciones, 
                               consumo_promedio_anterior=f"{consumo_promedio:.2f}",
                               clasificacion=clasificacion_actual)

    flash('Error de conexión a la base de datos.', 'error')
    return redirect(url_for('cuestionario'))

@app.route('/historial', methods=['GET'])
@login_required
def historial():
    """Muestra todos los registros de consumo del usuario."""
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    table = 'registro_casa' if user_type == 'casa' else 'registro_empresa'
    titulo = "Historial de Consumo - Hogar/Local" if user_type == 'casa' else "Historial de Consumo - Empresa"
    
    cnx = get_db_connection()
    registros = []
    if cnx:
        cursor = cnx.cursor(dictionary=True) # Usamos dictionary=True para MySQL
        query = f"SELECT id, fecha, consumo_kwh, clasificacion, antiguedad_equipo FROM {table} WHERE user_id = %s ORDER BY fecha DESC" 
        cursor.execute(query, (user_id,))
        registros = cursor.fetchall()
        cursor.close()
        cnx.close()
        
    return render_template('historial.html', registros=registros, titulo_apartado=titulo, user_type=user_type)


if __name__ == '__main__':
    app.run(debug=True)