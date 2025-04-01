const { createClient } = require('@supabase/supabase-js')

const supabase = createClient(
  'https://rhvisrtmewswqfebzjtl.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJodmlzcnRtZXdzd3FmZWJ6anRsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTA5ODEwNywiZXhwIjoyMDg2Njc0MTA3fQ.NKVJVvC1WbCpLzhwzU740NlbFMf3sZiWw3Io5ayTrOs'
)

async function checkSchema() {
  try {
    const { data, error } = await supabase
      .from('stores')
      .select('*')
      .limit(1)
    
    if (error) {
      console.log('Error:', error.message)
    } else {
      console.log('Stores table columns:', data.length > 0 ? Object.keys(data[0]) : 'No data')
    }
  } catch (err) {
    console.error('Error:', err)
  }
}

checkSchema()
