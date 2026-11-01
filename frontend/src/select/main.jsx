import { createRoot } from 'react-dom/client';
import { readConfig } from '../common/config.js';
import SelectApp from './SelectApp.jsx';

createRoot(document.getElementById('select-app')).render(<SelectApp config={readConfig()} />);
