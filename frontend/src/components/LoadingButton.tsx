import styles from './Button.module.css'
import { useNavigate } from 'react-router-dom';



function LoadingButton() {
    const navigate = useNavigate();

    const navigateToFlowPage = () => {
        navigate('/flow');
    };

    return (
        <button className={styles.button} onClick={navigateToFlowPage}>Continue</button> 
    );
}

export default LoadingButton;