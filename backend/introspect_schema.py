"""
Introspect Railway database schema and generate comprehensive report.
This script will help understand the new database structure for refactoring.

Usage:
    # Via Railway CLI (recommended)
    railway run python introspect_schema.py
    
    # Or locally with DATABASE_URL in .env file
    python introspect_schema.py
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Inspector

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, will rely on environment variables

def get_database_url():
    """Get database URL from environment or config."""
    # Prefer public URL if available (for local access)
    database_url = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
    
    if not database_url:
        # Try loading from config
        try:
            from app.config import get_settings
            settings = get_settings()
            database_url = settings.database_url
        except Exception as e:
            print(f"⚠️  Could not load from config: {e}")
            pass
    
    if not database_url:
        print("❌ DATABASE_URL not found")
        print("\nOptions:")
        print("1. Run via Railway: railway run python introspect_schema.py")
        print("2. Set locally: export DATABASE_URL=... or DATABASE_PUBLIC_URL=...")
        print("3. Add to .env file in backend/ directory")
        sys.exit(1)
    
    # Convert to psycopg format if needed
    if database_url.startswith('postgresql://') and '+psycopg' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://')
    
    return database_url


def introspect_schema():
    """Introspect the database schema and return structured data."""
    database_url = get_database_url()
    
    # Mask sensitive parts of URL for display
    if '@' in database_url:
        url_parts = database_url.split('@')
        if len(url_parts) > 1:
            masked_url = f"postgresql+psycopg://***@{url_parts[1]}"
        else:
            masked_url = "postgresql+psycopg://***"
    else:
        masked_url = "postgresql+psycopg://***"
    
    print(f"🔌 Connecting to database...")
    print(f"   URL: {masked_url}\n")
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    schema_info = {
        'timestamp': datetime.now().isoformat(),
        'database_url_masked': masked_url,
        'tables': {}
    }
    
    # Get all table names
    table_names = inspector.get_table_names()
    print(f"📋 Found {len(table_names)} tables: {', '.join(table_names)}\n")
    
    for table_name in table_names:
        print(f"📊 Analyzing table: {table_name}")
        
        # Get columns
        columns = []
        for column in inspector.get_columns(table_name):
            col_info = {
                'name': column['name'],
                'type': str(column['type']),
                'nullable': column['nullable'],
                'default': str(column['default']) if column['default'] is not None else None,
                'autoincrement': column.get('autoincrement', False),
            }
            columns.append(col_info)
        
        # Get primary keys
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_keys = pk_constraint.get('constrained_columns', [])
        
        # Get foreign keys
        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name):
            foreign_keys.append({
                'name': fk.get('name'),
                'constrained_columns': fk['constrained_columns'],
                'referred_table': fk['referred_table'],
                'referred_columns': fk['referred_columns'],
                'ondelete': fk.get('ondelete'),
                'onupdate': fk.get('onupdate'),
            })
        
        # Get indexes
        indexes = []
        for idx in inspector.get_indexes(table_name):
            indexes.append({
                'name': idx['name'],
                'column_names': idx['column_names'],
                'unique': idx['unique'],
            })
        
        # Get unique constraints
        unique_constraints = []
        for uc in inspector.get_unique_constraints(table_name):
            unique_constraints.append({
                'name': uc['name'],
                'column_names': uc['column_names'],
            })
        
        # Get sample data (first row to understand structure)
        sample_row = None
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 1"))
                row = result.fetchone()
                if row:
                    columns_names = result.keys()
                    sample_row = {col: str(val)[:200] if val is not None else None 
                                 for col, val in zip(columns_names, row)}
        except Exception as e:
            sample_row = {'error': str(e)}
        
        # Get row count
        row_count = None
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
        except:
            pass
        
        schema_info['tables'][table_name] = {
            'columns': columns,
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys,
            'indexes': indexes,
            'unique_constraints': unique_constraints,
            'sample_row': sample_row,
            'row_count': row_count,
        }
    
    return schema_info


def generate_sqlalchemy_models_stub(schema_info):
    """Generate SQLAlchemy model stubs based on schema."""
    models_code = []
    models_code.append("# Auto-generated SQLAlchemy model stubs based on Railway schema")
    models_code.append("# TODO: Review and adjust types, relationships, and constraints\n")
    models_code.append("from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, Numeric, Float")
    models_code.append("from sqlalchemy.dialects.postgresql import UUID, JSONB")
    models_code.append("from sqlalchemy.sql import func")
    models_code.append("from sqlalchemy.orm import relationship")
    models_code.append("import uuid")
    models_code.append("from app.database import Base\n\n")
    
    # Type mapping from PostgreSQL types to SQLAlchemy
    type_mapping = {
        'VARCHAR': 'String',
        'CHARACTER VARYING': 'String',
        'TEXT': 'Text',
        'INTEGER': 'Integer',
        'BIGINT': 'Integer',
        'SMALLINT': 'Integer',
        'BOOLEAN': 'Boolean',
        'TIMESTAMP': 'DateTime',
        'TIMESTAMP WITHOUT TIME ZONE': 'DateTime',
        'TIMESTAMPTZ': 'DateTime',
        'TIMESTAMP WITH TIME ZONE': 'DateTime',
        'UUID': 'UUID',
        'JSONB': 'JSONB',
        'JSON': 'JSONB',
        'NUMERIC': 'Numeric',
        'DECIMAL': 'Numeric',
        'FLOAT': 'Float',
        'REAL': 'Float',
        'DOUBLE PRECISION': 'Float',
    }
    
    for table_name, table_info in schema_info['tables'].items():
        class_name = ''.join(word.capitalize() for word in table_name.split('_'))
        models_code.append(f"class {class_name}(Base):")
        models_code.append(f'    __tablename__ = "{table_name}"\n')
        
        # Add columns
        for col in table_info['columns']:
            col_name = col['name']
            col_type_str = col['type']
            
            # Try to infer SQLAlchemy type
            sqlalchemy_type = 'String'  # default
            type_params = ''
            
            # Check for UUID
            if 'UUID' in col_type_str.upper():
                sqlalchemy_type = 'UUID(as_uuid=True)'
            # Check for VARCHAR with length
            elif 'VARCHAR' in col_type_str.upper() or 'CHARACTER VARYING' in col_type_str.upper():
                # Extract length if present
                if '(' in col_type_str:
                    try:
                        length = int(col_type_str.split('(')[1].split(')')[0])
                        sqlalchemy_type = f'String({length})'
                    except:
                        sqlalchemy_type = 'String'
                else:
                    sqlalchemy_type = 'String'
            # Check for other types
            else:
                for pg_type, sa_type in type_mapping.items():
                    if pg_type in col_type_str.upper():
                        sqlalchemy_type = sa_type
                        break
            
            # Build column definition
            col_def = f"    {col_name} = Column({sqlalchemy_type}"
            
            # Check if primary key
            if col_name in table_info['primary_keys']:
                col_def += ", primary_key=True"
                if 'UUID' in col_type_str.upper():
                    col_def += ", default=uuid.uuid4"
            
            # Check if foreign key
            for fk in table_info['foreign_keys']:
                if col_name in fk['constrained_columns']:
                    idx = fk['constrained_columns'].index(col_name)
                    ref_col = fk['referred_columns'][idx]
                    col_def += f", ForeignKey('{fk['referred_table']}.{ref_col}')"
            
            # Nullable
            if not col['nullable']:
                col_def += ", nullable=False"
            
            # Default
            if col['default']:
                if 'now()' in col['default'].lower() or 'current_timestamp' in col['default'].lower():
                    col_def += ", server_default=func.now()"
                elif 'uuid_generate' in col['default'].lower():
                    col_def += ", default=uuid.uuid4"
            
            col_def += ")"
            models_code.append(col_def)
        
        # Add relationships (simple version - needs manual review)
        if table_info['foreign_keys']:
            models_code.append("")
            models_code.append("    # TODO: Add relationships based on foreign keys")
            for fk in table_info['foreign_keys']:
                if len(fk['constrained_columns']) == 1:
                    col_name = fk['constrained_columns'][0]
                    ref_table = fk['referred_table']
                    ref_class = ''.join(word.capitalize() for word in ref_table.split('_'))
                    models_code.append(f"    # relationship to {ref_class} via {col_name}")
        
        models_code.append("\n")
    
    return '\n'.join(models_code)


def main():
    """Main function."""
    try:
        # Introspect schema
        schema_info = introspect_schema()
        
        # Save JSON output
        output_file = Path(__file__).parent / 'schema_introspection.json'
        with open(output_file, 'w') as f:
            json.dump(schema_info, f, indent=2, default=str)
        
        print(f"\n✅ Schema introspection complete!")
        print(f"📄 JSON saved to: {output_file}")
        
        # Generate model stubs
        models_stub = generate_sqlalchemy_models_stub(schema_info)
        models_file = Path(__file__).parent / 'schema_models_stub.py'
        with open(models_file, 'w') as f:
            f.write(models_stub)
        
        print(f"📄 SQLAlchemy model stubs saved to: {models_file}")
        
        # Print summary
        print(f"\n📊 Summary:")
        print(f"   Tables: {len(schema_info['tables'])}")
        for table_name, table_info in schema_info['tables'].items():
            print(f"   - {table_name}: {len(table_info['columns'])} columns, "
                  f"{len(table_info['foreign_keys'])} FKs, "
                  f"~{table_info.get('row_count', 'N/A')} rows")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Review {output_file} for detailed schema")
        print(f"   2. Review {models_file} for model stubs")
        print(f"   3. Compare with existing models in app/models/")
        print(f"   4. Begin refactoring based on new schema")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

