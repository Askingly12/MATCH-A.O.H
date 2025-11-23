from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# --- Rutas Principales ---

@app.route('/', methods=['GET'])
def index():
    """Muestra la página de bienvenida con las opciones de selección."""
    # Renderiza la plantilla principal (index.html)
    return render_template('index.html')

@app.route('/bienvenida/<tipo_usuario>', methods=['GET'])
def bienvenida(tipo_usuario):
    """Muestra la página de bienvenida específica según la opción elegida."""
    
    # Asignamos el nombre completo para mostrar en la página
    if tipo_usuario == 'casa':
        titulo = "Tu Casa o Local"
    elif tipo_usuario == 'empresa':
        titulo = "Tu Empresa"
    else:
        # Redirige a la página principal si el tipo es inválido
        return redirect(url_for('index'))
        
    # Renderiza la plantilla de bienvenida, pasándole el título
    return render_template('bienvenida.html', titulo_apartado=titulo)


if __name__ == '__main__':
    # Ejecuta la aplicación. debug=True es útil durante el desarrollo.
    app.run(debug=True)