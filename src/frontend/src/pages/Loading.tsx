import Loader from "../components/Loader"
import styles from "./Loading.module.css"

function Loading() {
    return (
        <div className={styles.loading}>
            <div>
                <h1>Loading</h1>
            </div>
            <div>
                <Loader/>
            </div>
        </div>
    );
}

export default Loading;