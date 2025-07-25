const { Pool } = require('pg');

// Database connection configuration - using the production connection from the project
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || "postgresql://reportmate:2sSWbVxyqjXp9WUpeMmzRaC@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require"
});

async function inspectSystemData() {
  let client;
  try {
    client = await pool.connect();
    
    // First, let's see what devices we have
    console.log('=== DEVICES TABLE ===');
    const devicesResult = await client.query('SELECT id, serial_number, name FROM devices LIMIT 5');
    console.log('Devices:', devicesResult.rows);
    
    // Now let's look at the system table data
    console.log('\n=== SYSTEM TABLE DATA ===');
    const systemResult = await client.query(`
      SELECT 
        device_id, 
        data->>'operatingSystem' as has_operating_system,
        jsonb_pretty(data) as formatted_data
      FROM system 
      LIMIT 1
    `);
    
    if (systemResult.rows.length > 0) {
      console.log('System data for device:', systemResult.rows[0].device_id);
      console.log('Has operatingSystem?:', systemResult.rows[0].has_operating_system ? 'YES' : 'NO');
      console.log('\nFull system data:');
      console.log(systemResult.rows[0].formatted_data);
    } else {
      console.log('No system data found in database');
    }
    
    // Check if operatingSystem exists in any system records
    console.log('\n=== OPERATING SYSTEM DATA CHECK ===');
    const osCheckResult = await client.query(`
      SELECT 
        device_id,
        data->'operatingSystem'->>'name' as os_name,
        data->'operatingSystem'->>'version' as os_version,
        data->'operatingSystem'->>'build' as os_build,
        data->'operatingSystem'->>'architecture' as os_architecture
      FROM system 
      WHERE data->>'operatingSystem' IS NOT NULL
      LIMIT 5
    `);
    
    if (osCheckResult.rows.length > 0) {
      console.log('Devices with operatingSystem data:');
      osCheckResult.rows.forEach(row => {
        console.log(`Device ${row.device_id}: ${row.os_name} ${row.os_version} (${row.os_architecture})`);
      });
    } else {
      console.log('NO devices found with operatingSystem data in system table');
    }
    
  } catch (error) {
    console.error('Database error:', error);
  } finally {
    if (client) {
      client.release();
    }
  }
}

inspectSystemData().then(() => {
  process.exit(0);
}).catch(error => {
  console.error('Script error:', error);
  process.exit(1);
});
