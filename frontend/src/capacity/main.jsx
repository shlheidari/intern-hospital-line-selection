import { createRoot } from 'react-dom/client';
import { readConfig } from '../common/config.js';
import CapacityApp from './CapacityApp.jsx';

createRoot(document.getElementById('capacity-app')).render(<CapacityApp config={readConfig()} />);
