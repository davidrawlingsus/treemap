"""
Database management routes for founder admin.
Provides direct access to database tables for admin purposes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from uuid import UUID
from datetime import datetime
from typing import List, Optional
import logging

from app.database import get_db, engine
from app.models import User
from app.schemas import (
    TableInfo,
    ColumnInfo,
    TableDataResponse,
    RowCreateRequest,
    RowUpdateRequest,
    TableCreateRequest,
    ColumnAddRequest,
)
from app.auth import get_current_active_founder_with_password

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/founder/database/tables", response_model=List[TableInfo])
def list_database_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """List all tables in the database with their column information."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    result = []
    for table_name in tables:
        # Skip alembic version table
        if table_name == 'alembic_version':
            continue
            
        columns = inspector.get_columns(table_name)
        column_info = []
        
        for col in columns:
            # Get primary key info
            pk_constraint = inspector.get_pk_constraint(table_name)
            is_pk = col['name'] in (pk_constraint.get('constrained_columns', []) or [])
            
            # Get foreign key info
            fk_info = None
            foreign_keys = inspector.get_foreign_keys(table_name)
            for fk in foreign_keys:
                if col['name'] in fk.get('constrained_columns', []):
                    fk_info = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                    break
            
            # Convert SQLAlchemy type to string
            col_type = str(col['type'])
            # Simplify type names
            if 'VARCHAR' in col_type or 'TEXT' in col_type or 'CHAR' in col_type:
                col_type = 'string'
            elif 'INTEGER' in col_type or 'BIGINT' in col_type or 'SMALLINT' in col_type:
                col_type = 'integer'
            elif 'BOOLEAN' in col_type:
                col_type = 'boolean'
            elif 'TIMESTAMP' in col_type or 'DATETIME' in col_type:
                col_type = 'datetime'
            elif 'UUID' in col_type:
                col_type = 'uuid'
            elif 'JSON' in col_type or 'JSONB' in col_type:
                col_type = 'json'
            elif 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type or 'REAL' in col_type:
                col_type = 'numeric'
            
            column_info.append(ColumnInfo(
                name=col['name'],
                type=col_type,
                nullable=col.get('nullable', True),
                primary_key=is_pk,
                foreign_key=fk_info,
                default=str(col.get('default', '')) if col.get('default') is not None else None
            ))
        
        # Get row count
        try:
            row_count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = row_count_result.scalar()
        except Exception:
            row_count = None
        
        result.append(TableInfo(
            name=table_name,
            row_count=row_count,
            columns=column_info
        ))
    
    # Sort by table name
    result.sort(key=lambda x: x.name)
    return result


@router.get("/api/founder/database/tables/{table_name}/columns", response_model=List[ColumnInfo])
def get_table_columns(
    table_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Get column information for a specific table."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    columns = inspector.get_columns(table_name)
    pk_constraint = inspector.get_pk_constraint(table_name)
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    result = []
    for col in columns:
        is_pk = col['name'] in (pk_constraint.get('constrained_columns', []) or [])
        
        fk_info = None
        for fk in foreign_keys:
            if col['name'] in fk.get('constrained_columns', []):
                fk_info = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                break
        
        col_type = str(col['type'])
        if 'VARCHAR' in col_type or 'TEXT' in col_type or 'CHAR' in col_type:
            col_type = 'string'
        elif 'INTEGER' in col_type or 'BIGINT' in col_type or 'SMALLINT' in col_type:
            col_type = 'integer'
        elif 'BOOLEAN' in col_type:
            col_type = 'boolean'
        elif 'TIMESTAMP' in col_type or 'DATETIME' in col_type:
            col_type = 'datetime'
        elif 'UUID' in col_type:
            col_type = 'uuid'
        elif 'JSON' in col_type or 'JSONB' in col_type:
            col_type = 'json'
        elif 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type or 'REAL' in col_type:
            col_type = 'numeric'
        
        result.append(ColumnInfo(
            name=col['name'],
            type=col_type,
            nullable=col.get('nullable', True),
            primary_key=is_pk,
            foreign_key=fk_info,
            default=str(col.get('default', '')) if col.get('default') is not None else None
        ))
    
    return result


@router.get("/api/founder/database/tables/{table_name}/data", response_model=TableDataResponse)
def get_table_data(
    table_name: str,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Get paginated data from a specific table."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get column info
    columns = inspector.get_columns(table_name)
    pk_constraint = inspector.get_pk_constraint(table_name)
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    column_info = []
    pk_columns = pk_constraint.get('constrained_columns', []) or []
    
    for col in columns:
        is_pk = col['name'] in pk_columns
        
        fk_info = None
        for fk in foreign_keys:
            if col['name'] in fk.get('constrained_columns', []):
                fk_info = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                break
        
        col_type = str(col['type'])
        if 'VARCHAR' in col_type or 'TEXT' in col_type or 'CHAR' in col_type:
            col_type = 'string'
        elif 'INTEGER' in col_type or 'BIGINT' in col_type or 'SMALLINT' in col_type:
            col_type = 'integer'
        elif 'BOOLEAN' in col_type:
            col_type = 'boolean'
        elif 'TIMESTAMP' in col_type or 'DATETIME' in col_type:
            col_type = 'datetime'
        elif 'UUID' in col_type:
            col_type = 'uuid'
        elif 'JSON' in col_type or 'JSONB' in col_type:
            col_type = 'json'
        elif 'NUMERIC' in col_type or 'DECIMAL' in col_type or 'FLOAT' in col_type or 'REAL' in col_type:
            col_type = 'numeric'
        
        column_info.append(ColumnInfo(
            name=col['name'],
            type=col_type,
            nullable=col.get('nullable', True),
            primary_key=is_pk,
            foreign_key=fk_info,
            default=str(col.get('default', '')) if col.get('default') is not None else None
        ))
    
    # Get total count
    count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    total = count_result.scalar()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    
    # Get paginated data
    # Build ORDER BY clause using primary key or first column
    order_by_col = pk_columns[0] if pk_columns else columns[0]['name']
    query = text(f"SELECT * FROM {table_name} ORDER BY {order_by_col} LIMIT :limit OFFSET :offset")
    
    result = db.execute(query, {"limit": page_size, "offset": offset})
    rows = []
    
    for row in result:
        row_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Convert UUID, datetime, and JSON types to serializable format
            if value is None:
                row_dict[col['name']] = None
            elif isinstance(value, UUID):
                row_dict[col['name']] = str(value)
            elif isinstance(value, datetime):
                row_dict[col['name']] = value.isoformat()
            elif isinstance(value, (dict, list)):
                row_dict[col['name']] = value
            else:
                row_dict[col['name']] = value
        rows.append(row_dict)
    
    return TableDataResponse(
        table_name=table_name,
        columns=column_info,
        rows=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/api/founder/database/tables/{table_name}/rows")
def create_table_row(
    table_name: str,
    request: RowCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Create a new row in a table."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    columns = inspector.get_columns(table_name)
    column_names = {col['name'] for col in columns}
    
    # Validate that all provided fields exist as columns
    invalid_fields = set(request.data.keys()) - column_names
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields: {', '.join(invalid_fields)}"
        )
    
    # Build INSERT statement
    valid_fields = {k: v for k, v in request.data.items() if k in column_names}
    if not valid_fields:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    
    field_names = ', '.join(valid_fields.keys())
    placeholders = ', '.join([f":{name}" for name in valid_fields.keys()])
    
    try:
        query = text(f"INSERT INTO {table_name} ({field_names}) VALUES ({placeholders}) RETURNING *")
        result = db.execute(query, valid_fields)
        db.commit()
        
        row = result.fetchone()
        if row:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, UUID):
                    row_dict[col['name']] = str(value)
                elif isinstance(value, datetime):
                    row_dict[col['name']] = value.isoformat()
                else:
                    row_dict[col['name']] = value
            return {"message": "Row created successfully", "row": row_dict}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create row: {str(e)}")


@router.put("/api/founder/database/tables/{table_name}/rows")
def update_table_row(
    table_name: str,
    request: RowUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Update a row in a table. Requires 'id' field to identify the row."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get primary key columns
    pk_constraint = inspector.get_pk_constraint(table_name)
    pk_columns = pk_constraint.get('constrained_columns', []) or []
    
    if not pk_columns:
        raise HTTPException(
            status_code=400,
            detail="Table has no primary key. Cannot safely update rows."
        )
    
    # Extract primary key values from request data
    pk_values = {}
    update_values = {}
    
    for key, value in request.data.items():
        if key in pk_columns:
            pk_values[key] = value
        else:
            update_values[key] = value
    
    if not pk_values:
        raise HTTPException(
            status_code=400,
            detail=f"Primary key value(s) required: {', '.join(pk_columns)}"
        )
    
    if not update_values:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Validate that update fields exist as columns
    columns = inspector.get_columns(table_name)
    column_names = {col['name'] for col in columns}
    invalid_fields = set(update_values.keys()) - column_names
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fields: {', '.join(invalid_fields)}"
        )
    
    # Build UPDATE statement with WHERE clause
    set_clauses = ', '.join([f"{name} = :{name}" for name in update_values.keys()])
    where_clauses = ' AND '.join([f"{name} = :pk_{name}" for name in pk_values.keys()])
    
    # Merge parameters
    params = update_values.copy()
    for key, value in pk_values.items():
        params[f"pk_{key}"] = value
    
    try:
        query = text(f"UPDATE {table_name} SET {set_clauses} WHERE {where_clauses} RETURNING *")
        result = db.execute(query, params)
        db.commit()
        
        updated_row = result.fetchone()
        if not updated_row:
            raise HTTPException(status_code=404, detail="Row not found or not updated")
        
        row_dict = {}
        for i, col in enumerate(columns):
            value = updated_row[i]
            if isinstance(value, UUID):
                row_dict[col['name']] = str(value)
            elif isinstance(value, datetime):
                row_dict[col['name']] = value.isoformat()
            else:
                row_dict[col['name']] = value
        
        return {"message": "Row updated successfully", "row": row_dict}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update row: {str(e)}")


@router.delete("/api/founder/database/tables/{table_name}/rows")
def delete_table_row(
    table_name: str,
    id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Delete a row from a table. Requires 'id' query parameter."""
    if not id:
        raise HTTPException(status_code=400, detail="'id' parameter required")
    
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get primary key columns
    pk_constraint = inspector.get_pk_constraint(table_name)
    pk_columns = pk_constraint.get('constrained_columns', []) or []
    
    if not pk_columns:
        raise HTTPException(
            status_code=400,
            detail="Table has no primary key. Cannot safely delete rows."
        )
    
    # Use first primary key column (usually 'id')
    pk_column = pk_columns[0]
    
    try:
        query = text(f"DELETE FROM {table_name} WHERE {pk_column} = :id RETURNING *")
        result = db.execute(query, {"id": id})
        db.commit()
        
        deleted_row = result.fetchone()
        if not deleted_row:
            raise HTTPException(status_code=404, detail="Row not found")
        
        return {"message": "Row deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete row: {str(e)}")


@router.post("/api/founder/database/tables")
def create_table(
    request: TableCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Create a new table. ⚠️ DANGEROUS: Schema changes can break the application."""
    inspector = inspect(engine)
    
    if request.table_name in inspector.get_table_names():
        raise HTTPException(
            status_code=400,
            detail=f"Table '{request.table_name}' already exists"
        )
    
    # Validate table name (prevent SQL injection)
    if not request.table_name.replace('_', '').isalnum():
        raise HTTPException(
            status_code=400,
            detail="Table name can only contain letters, numbers, and underscores"
        )
    
    # Build CREATE TABLE statement
    column_defs = []
    for col in request.columns:
        col_name = col.get('name', '').replace('"', '')
        col_type = col.get('type', 'TEXT').upper()
        nullable = 'NULL' if col.get('nullable', True) else 'NOT NULL'
        default = f" DEFAULT {col.get('default')}" if col.get('default') is not None else ''
        
        column_defs.append(f'"{col_name}" {col_type} {nullable}{default}')
    
    try:
        create_sql = f'CREATE TABLE "{request.table_name}" ({", ".join(column_defs)})'
        db.execute(text(create_sql))
        db.commit()
        
        return {"message": f"Table '{request.table_name}' created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create table: {str(e)}")


@router.post("/api/founder/database/tables/{table_name}/columns")
def add_table_column(
    table_name: str,
    request: ColumnAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Add a column to a table. ⚠️ DANGEROUS: Schema changes can break the application."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Check if column already exists
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    if request.column_name in existing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Column '{request.column_name}' already exists"
        )
    
    # Validate column name
    if not request.column_name.replace('_', '').isalnum():
        raise HTTPException(
            status_code=400,
            detail="Column name can only contain letters, numbers, and underscores"
        )
    
    nullable = 'NULL' if request.nullable else 'NOT NULL'
    default_clause = f" DEFAULT {request.default}" if request.default is not None else ''
    
    try:
        alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{request.column_name}" {request.column_type.upper()} {nullable}{default_clause}'
        db.execute(text(alter_sql))
        db.commit()
        
        return {"message": f"Column '{request.column_name}' added successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to add column: {str(e)}")


@router.delete("/api/founder/database/tables/{table_name}")
def delete_table(
    table_name: str,
    confirm: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Delete a table. ⚠️ DANGEROUS: This will permanently delete all data in the table."""
    # Handle confirm parameter - FastAPI query params come as strings
    if confirm is None or confirm.lower() not in ('true', '1', 'yes'):
        raise HTTPException(
            status_code=400,
            detail="Deletion requires explicit confirmation. Set 'confirm=true' parameter."
        )
    
    inspector = inspect(engine)
    
    # Get list of tables - use exact name from database
    table_names = inspector.get_table_names()
    if table_name not in table_names:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    # Get the exact table name as it appears in PostgreSQL (handles case sensitivity)
    # Since inspector returns the actual names, we should use the exact match
    actual_table_name = table_name  # Use the parameter which should match exactly
    
    try:
        # PostgreSQL: unquoted identifiers are lowercased, quoted preserve case
        # Try with quotes first (most common), then without if needed
        # Use CASCADE to handle foreign key constraints
        try:
            # Use the exact table name with quotes to preserve any case sensitivity
            drop_sql = text(f'DROP TABLE "{actual_table_name}" CASCADE')
            result = db.execute(drop_sql)
            logger.info(f"Executed: DROP TABLE \"{actual_table_name}\" CASCADE")
        except Exception as first_error:
            # If quoted version fails (rare), try unquoted lowercase
            logger.warning(f"Quoted drop failed for {actual_table_name}, trying unquoted: {first_error}")
            drop_sql = text(f'DROP TABLE {actual_table_name.lower()} CASCADE')
            result = db.execute(drop_sql)
            actual_table_name = actual_table_name.lower()
        
        db.commit()
        
        # Verify deletion by checking if table still exists
        fresh_inspector = inspect(engine)
        remaining_tables = fresh_inspector.get_table_names()
        if actual_table_name in remaining_tables or table_name in remaining_tables:
            logger.error(f"Table {table_name} still exists after deletion. Remaining: {remaining_tables}")
            raise HTTPException(
                status_code=500,
                detail=f"Table '{table_name}' still exists after deletion attempt. Remaining tables: {', '.join(remaining_tables[:5])}"
            )
        
        logger.info(f"Successfully deleted table: {table_name}")
        return {"message": f"Table '{table_name}' deleted successfully"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"Failed to delete table {table_name}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to delete table: {error_msg}")


@router.delete("/api/founder/database/tables/{table_name}/columns/{column_name}")
def delete_table_column(
    table_name: str,
    column_name: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_founder_with_password),
):
    """Delete a column from a table. ⚠️ DANGEROUS: This will permanently delete all data in the column."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion requires explicit confirmation. Set 'confirm=true' parameter."
        )
    
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    if column_name not in existing_columns:
        raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found")
    
    try:
        alter_sql = f'ALTER TABLE "{table_name}" DROP COLUMN "{column_name}" CASCADE'
        db.execute(text(alter_sql))
        db.commit()
        
        return {"message": f"Column '{column_name}' deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete column: {str(e)}")

