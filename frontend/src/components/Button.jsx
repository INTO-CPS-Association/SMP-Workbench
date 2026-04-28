import styles from './Button.module.css'
import { useNavigate } from 'react-router-dom';



function Button() {
    const navigate = useNavigate();

    const navigateToLoadingPage = () => {
        navigate('/loading');
    };

    return (
        <button className={styles.button} onClick={navigateToLoadingPage}>GO</button> 
    );
}

export default Button;
